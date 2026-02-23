import 'package:flutter/material.dart';
import '../features/auth/pages/login_page.dart';
import '../features/dashboard/pages/dashboard_page.dart';
import '../features/dashboard/pages/graph_page.dart';
import '../features/dashboard/pages/leaderboard_page.dart';
import '../features/dashboard/bloc/dashboard_bloc.dart';
import '../features/diagnostic/pages/diagnostic_page.dart';
import '../features/exam/pages/exam_page.dart';
import '../features/practice/pages/practice_page.dart';

Route<dynamic>? onGenerateRoute(RouteSettings settings) {
  return switch (settings.name) {
    '/' || DashboardPage.routeName => MaterialPageRoute(
        builder: (_) => const DashboardPage(), settings: settings),
    LoginPage.routeName => MaterialPageRoute(
        builder: (_) => const LoginPage(), settings: settings),
    PracticePage.routeName => MaterialPageRoute(
        builder: (_) {
          final args = settings.arguments as Map<String, dynamic>?;
          return PracticePage(
            tag: args?['tag'] as String?,
            tagName: args?['tagName'] as String?,
            nodeId: args?['nodeId'] as String?,
          );
        },
        settings: settings),
    GraphPage.routeName => MaterialPageRoute(
        builder: (_) => const GraphPage(), settings: settings),
    DiagnosticPage.routeName => MaterialPageRoute(
        builder: (_) => const DiagnosticPage(), settings: settings),
    LeaderboardPage.routeName => MaterialPageRoute(
        builder: (_) {
          final entries =
              settings.arguments as List<LeaderboardEntry>? ?? [];
          return LeaderboardPage(entries: entries);
        },
        settings: settings),
    ExamPage.routeName => MaterialPageRoute(
        builder: (_) => const ExamPage(), settings: settings),
    _ => MaterialPageRoute(
        builder: (_) =>
            const Scaffold(body: Center(child: Text('404')))),
  };
}
