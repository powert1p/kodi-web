import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import 'app/config.dart';
import 'app/router.dart';
import 'app/theme.dart';
import 'features/auth/bloc/auth_bloc.dart';
import 'features/auth/pages/login_page.dart';
import 'features/dashboard/bloc/dashboard_bloc.dart';
import 'features/dashboard/pages/dashboard_page.dart';

void main() {
  runApp(const NisMathApp());
}

class _SmoothScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
    PointerDeviceKind.touch, PointerDeviceKind.mouse,
    PointerDeviceKind.trackpad, PointerDeviceKind.stylus,
  };
  @override
  ScrollPhysics getScrollPhysics(BuildContext context) =>
    const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics());
}

class NisMathApp extends StatelessWidget {
  const NisMathApp({super.key});

  @override
  Widget build(BuildContext context) {
    final api = NisApiClient(baseUrl: AppConfig.apiBaseUrl);

    return MultiRepositoryProvider(
      providers: [RepositoryProvider<NisApiClient>.value(value: api)],
      child: MultiBlocProvider(
        providers: [
          BlocProvider(create: (_) => AuthBloc(api: api)..add(AuthCheckRequested())),
          BlocProvider(create: (_) => DashboardBloc(api: api)),
        ],
        child: MaterialApp(
          scrollBehavior: _SmoothScrollBehavior(),
          title: 'NIS Math',
          theme: AppTheme.light,
          debugShowCheckedModeBanner: false,
          onGenerateRoute: onGenerateRoute,
          home: BlocBuilder<AuthBloc, AuthState>(
            builder: (context, state) => switch (state) {
              AuthAuthenticated() => const DashboardPage(),
              AuthUnauthenticated() => const LoginPage(),
              _ => const Scaffold(body: Center(child: CircularProgressIndicator())),
            },
          ),
        ),
      ),
    );
  }
}
