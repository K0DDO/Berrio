import 'package:flutter_test/flutter_test.dart';
import 'package:berrio/features/home/data/dashboard_api.dart';

void main() {
  test('DashboardDto parses aggregate payload', () {
    final dto = DashboardDto.fromJson({
      'berrio_score': {'score': 72, 'factors': {}},
      'spending': {
        'current_month': '1200.00',
        'previous_month': '1000.00',
        'change_pct': 20.0,
        'budget_limit': '5000.00',
        'currency': 'RUB',
      },
      'category_trends': [
        {
          'category_name': 'Food',
          'current_amount': '500',
          'previous_amount': '400',
          'change_pct': 25.0,
          'direction': 'up',
        }
      ],
      'active_goals': [
        {
          'id': '11111111-1111-1111-1111-111111111111',
          'name': 'Trip',
          'progress_pct': 40.0,
          'current_amount': '4000',
          'target_amount': '10000',
          'currency': 'RUB',
          'status': 'ACTIVE',
        }
      ],
      'recent_notifications': [
        {
          'id': '22222222-2222-2222-2222-222222222222',
          'type': 'BUDGET_WARNING',
          'title': 'Budget',
          'message': 'Almost there',
          'severity': 'WARNING',
          'created_at': '2026-07-18T10:00:00Z',
        }
      ],
      'ai_recommendation': {
        'title': 'Focus',
        'body': 'Trim food spend',
        'kind': 'spend_focus',
      },
    });
    expect(dto.score, 72);
    expect(dto.changePct, 20.0);
    expect(dto.goals.first.name, 'Trip');
    expect(dto.aiTitle, 'Focus');
  });
}
