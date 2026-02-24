import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../features/auth/pages/login_page.dart';
import '../features/dashboard/pages/dashboard_page.dart';
import '../features/dashboard/pages/graph_page.dart';
import '../features/dashboard/pages/leaderboard_page.dart';
import '../features/dashboard/bloc/dashboard_bloc.dart';
import '../features/diagnostic/pages/diagnostic_page.dart';
import '../features/diagnostic/bloc/diagnostic_bloc.dart';
import '../features/exam/pages/exam_page.dart';
import '../features/exam/bloc/exam_bloc.dart';
import '../features/practice/pages/practice_page.dart';
import '../features/practice/bloc/practice_bloc.dart';

Route<dynamic>? onGenerateRoute(RouteSettings settings) {
  return switch (settings.name) {
    '/' || DashboardPage.routeName => MaterialPageRoute(
        builder: (_) => const DashboardPage(), settings: settings),
    LoginPage.routeName => MaterialPageRoute(
        builder: (_) => const LoginPage(), settings: settings),
    PracticePage.routeName => MaterialPageRoute(
        builder: (ctx) {
          final args = settings.arguments as Map<String, dynamic>?;
          return BlocProvider(
            create: (ctx) => PracticeBloc(api: ctx.read<NisApiClient>())
              ..add(PracticeStarted(
                tag: args?['tag'] as String?,
                nodeId: args?['nodeId'] as String?,
              )),
            child: PracticePage(
              tagName: args?['tagName'] as String?,
            ),
          );
        },
        settings: settings),
    GraphPage.routeName => MaterialPageRoute(
        builder: (_) => const GraphPage(), settings: settings),
    DiagnosticPage.routeName => MaterialPageRoute(
        builder: (ctx) => BlocProvider(
          create: (ctx) => DiagnosticBloc(api: ctx.read<NisApiClient>())
            ..add(DiagnosticCheckSession()),
          child: const DiagnosticPage(),
        ),
        settings: settings),
    LeaderboardPage.routeName => MaterialPageRoute(
        builder: (_) {
          final entries =
              settings.arguments as List<LeaderboardEntry>? ?? [];
          return LeaderboardPage(entries: entries);
        },
        settings: settings),
    ExamPage.routeName => MaterialPageRoute(
        builder: (ctx) => BlocProvider(
          create: (ctx) => ExamBloc(api: ctx.read<NisApiClient>()),
          child: const ExamPage(),
        ),
        settings: settings),
    _ => MaterialPageRoute(
        builder: (_) =>
            const Scaffold(body: Center(child: Text('404')))),
  };
}
