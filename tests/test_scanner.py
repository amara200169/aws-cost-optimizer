import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ─── get_cost_summary ─────────────────────────────────────────────────────────

class TestGetCostSummary:

    def test_returns_formatted_total(self):
        mock_response = {
            'ResultsByTime': [
                {'Total': {'UnblendedCost': {'Amount': '12.50', 'Unit': 'USD'}}},
                {'Total': {'UnblendedCost': {'Amount': '7.75', 'Unit': 'USD'}}},
            ]
        }
        with patch('boto3.client') as mock_boto:
            mock_ce = MagicMock()
            mock_ce.get_cost_and_usage.return_value = mock_response
            mock_boto.return_value = mock_ce

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ce = mock_ce

            result = scanner.get_cost_summary()
            assert result == '$20.25'

    def test_returns_zero_when_no_results(self):
        mock_response = {'ResultsByTime': []}
        with patch('boto3.client') as mock_boto:
            mock_ce = MagicMock()
            mock_ce.get_cost_and_usage.return_value = mock_response
            mock_boto.return_value = mock_ce

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ce = mock_ce

            result = scanner.get_cost_summary()
            assert result == '$0.00'

    def test_returns_na_on_api_error(self):
        with patch('boto3.client') as mock_boto:
            mock_ce = MagicMock()
            mock_ce.get_cost_and_usage.side_effect = Exception("AccessDenied")
            mock_boto.return_value = mock_ce

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ce = mock_ce

            result = scanner.get_cost_summary()
            assert result == 'N/A'


# ─── get_idle_instances ───────────────────────────────────────────────────────

class TestGetIdleInstances:

    def _make_instance(self, instance_id='i-abc123', instance_type='t3.micro'):
        return {
            'InstanceId': instance_id,
            'InstanceType': instance_type,
            'LaunchTime': datetime(2025, 1, 1, tzinfo=timezone.utc),
        }

    def _make_paginator(self, instances):
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {'Reservations': [{'Instances': instances}]}
        ]
        return paginator

    def test_idle_instance_is_detected(self):
        instance = self._make_instance()
        datapoints = [{'Average': 1.0}, {'Average': 2.0}]

        with patch('boto3.client') as mock_boto:
            mock_ec2 = MagicMock()
            mock_cw = MagicMock()
            mock_ec2.get_paginator.return_value = self._make_paginator([instance])
            mock_cw.get_metric_statistics.return_value = {'Datapoints': datapoints}

            def client_factory(service, **kwargs):
                return mock_ec2 if service == 'ec2' else mock_cw

            mock_boto.side_effect = client_factory

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ec2 = mock_ec2
            scanner.cloudwatch = mock_cw

            result = scanner.get_idle_instances()

            assert len(result) == 1
            assert result[0]['id'] == 'i-abc123'
            assert result[0]['avg_cpu'] == 1.5
            assert result[0]['type'] == 't3.micro'

    def test_active_instance_is_excluded(self):
        instance = self._make_instance()
        datapoints = [{'Average': 80.0}, {'Average': 75.0}]

        with patch('boto3.client') as mock_boto:
            mock_ec2 = MagicMock()
            mock_cw = MagicMock()
            mock_ec2.get_paginator.return_value = self._make_paginator([instance])
            mock_cw.get_metric_statistics.return_value = {'Datapoints': datapoints}

            def client_factory(service, **kwargs):
                return mock_ec2 if service == 'ec2' else mock_cw

            mock_boto.side_effect = client_factory

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ec2 = mock_ec2
            scanner.cloudwatch = mock_cw

            result = scanner.get_idle_instances()
            assert result == []

    def test_no_datapoints_treated_as_idle(self):
        instance = self._make_instance()

        with patch('boto3.client') as mock_boto:
            mock_ec2 = MagicMock()
            mock_cw = MagicMock()
            mock_ec2.get_paginator.return_value = self._make_paginator([instance])
            mock_cw.get_metric_statistics.return_value = {'Datapoints': []}

            def client_factory(service, **kwargs):
                return mock_ec2 if service == 'ec2' else mock_cw

            mock_boto.side_effect = client_factory

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ec2 = mock_ec2
            scanner.cloudwatch = mock_cw

            result = scanner.get_idle_instances()
            assert len(result) == 1
            assert result[0]['avg_cpu'] == 0.0

    def test_cloudwatch_error_skips_instance(self):
        instance = self._make_instance()

        with patch('boto3.client') as mock_boto:
            mock_ec2 = MagicMock()
            mock_cw = MagicMock()
            mock_ec2.get_paginator.return_value = self._make_paginator([instance])
            mock_cw.get_metric_statistics.side_effect = Exception("ThrottlingException")

            def client_factory(service, **kwargs):
                return mock_ec2 if service == 'ec2' else mock_cw

            mock_boto.side_effect = client_factory

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ec2 = mock_ec2
            scanner.cloudwatch = mock_cw

            result = scanner.get_idle_instances()
            assert result == []

    def test_empty_account_returns_empty_list(self):
        with patch('boto3.client') as mock_boto:
            mock_ec2 = MagicMock()
            mock_ec2.get_paginator.return_value = self._make_paginator([])

            mock_boto.return_value = mock_ec2

            import importlib, scanner
            importlib.reload(scanner)
            scanner.ec2 = mock_ec2

            result = scanner.get_idle_instances()
            assert result == []


# ─── _estimate_monthly_cost ───────────────────────────────────────────────────

class TestEstimateMonthlyCost:

    def test_known_instance_type(self):
        import scanner
        result = scanner._estimate_monthly_cost('t3.micro')
        assert result == '$7.49'

    def test_unknown_instance_type_uses_fallback(self):
        import scanner
        result = scanner._estimate_monthly_cost('z99.unknown')
        assert result.startswith('$')
        assert float(result[1:]) > 0

    def test_large_instance_costs_more_than_micro(self):
        import scanner
        micro = float(scanner._estimate_monthly_cost('t3.micro')[1:])
        large = float(scanner._estimate_monthly_cost('m5.4xlarge')[1:])
        assert large > micro


# ─── auto_remediate ───────────────────────────────────────────────────────────

class TestAutoRemediate:

    def _idle_instance(self):
        return {
            'id': 'i-abc123',
            'type': 't3.micro',
            'avg_cpu': 1.2,
            'estimated_monthly_cost': '$7.49',
            'launch_time': '2025-01-01T00:00:00+00:00',
        }

    def test_dry_run_does_not_stop_instances(self):
        with patch('scanner.get_idle_instances', return_value=[self._idle_instance()]):
            with patch('scanner.ec2') as mock_ec2:
                import scanner
                result = scanner.auto_remediate(dry_run=True)
                mock_ec2.stop_instances.assert_not_called()
                assert result == 0

    def test_live_mode_stops_idle_instances(self):
        with patch('scanner.get_idle_instances', return_value=[self._idle_instance()]):
            with patch('scanner.ec2') as mock_ec2:
                import scanner
                result = scanner.auto_remediate(dry_run=False)
                mock_ec2.stop_instances.assert_called_once_with(InstanceIds=['i-abc123'])
                assert result == 1

    def test_stop_error_is_handled_gracefully(self):
        with patch('scanner.get_idle_instances', return_value=[self._idle_instance()]):
            with patch('scanner.ec2') as mock_ec2:
                mock_ec2.stop_instances.side_effect = Exception("UnauthorizedOperation")
                import scanner
                result = scanner.auto_remediate(dry_run=False)
                assert result == 0

    def test_returns_zero_when_no_idle_instances(self):
        with patch('scanner.get_idle_instances', return_value=[]):
            import scanner
            result = scanner.auto_remediate(dry_run=False)
            assert result == 0
