import 'dart:convert';
import '../../../app/config.dart';
import '../../../app/colors.dart';
import '../../../app/locale_bloc.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_web/l10n/app_localizations.dart';
import '../../../app/error_l10n.dart';
import '../bloc/auth_bloc.dart';
import '../../dashboard/pages/dashboard_page.dart';
import 'phone_login_page.dart';
import '../../../shared/utils/responsive.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});
  static const routeName = '/login';

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  html.WindowBase? _popup;

  @override
  void initState() {
    super.initState();
    html.window.onMessage.listen(_onMessage);
  }

  void _onMessage(html.MessageEvent event) {
    try {
      final decoded = jsonDecode(event.data as String) as Map<String, dynamic>;
      if (decoded['type'] == 'tg_auth') {
        final data = decoded['data'] as Map<String, dynamic>;
        _popup?.close();
        if (mounted) {
          context.read<AuthBloc>().add(AuthTelegramLogin(data));
        }
      }
    } catch (e, st) {
      debugPrint('[LoginPage._onMessage] $e\n$st');
    }
  }

  void _openTelegramLogin() {
    final url = Uri.base.resolve('telegram_login.html?bot=${AppConfig.telegramBotName}').toString();
    _popup = html.window.open(
      url,
      'tg_login',
      'width=400,height=500,left=200,top=100',
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state is AuthAuthenticated) {
          Navigator.of(context).pushReplacementNamed(DashboardPage.routeName);
        }
      },
      child: Scaffold(
        backgroundColor: AppColors.loginBg,
        body: SafeArea(
          child: Stack(
            children: [
              // Language toggle — top right
              Positioned(
                top: 12,
                right: 16,
                child: BlocBuilder<LocaleBloc, LocaleState>(
                  builder: (context, localeState) {
                    final isRu = localeState.locale.languageCode == 'ru';
                    return TextButton(
                      onPressed: () {
                        final next = isRu ? const Locale('kk') : const Locale('ru');
                        context.read<LocaleBloc>().add(LocaleChanged(next));
                      },
                      child: Text(
                        isRu ? 'Қазақша' : 'Русский',
                        style: TextStyle(color: Colors.grey[600], fontWeight: FontWeight.w500),
                      ),
                    );
                  },
                ),
              ),
              Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Card(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: rp(context, 40), vertical: rp(context, 48)),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: rs(context, 72), height: rs(context, 72),
                        decoration: BoxDecoration(
                          color: AppColors.primary,
                          borderRadius: BorderRadius.circular(20)),
                        child: Icon(Icons.school_rounded, color: Colors.white, size: rs(context, 40))),
                      const SizedBox(height: 24),
                      Text('NIS Math',
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Text(l.loginSubtitle,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
                          textAlign: TextAlign.center),
                      const SizedBox(height: 32),

                      // Phone auth (primary)
                      BlocBuilder<AuthBloc, AuthState>(
                        builder: (context, state) {
                          if (state is AuthLoading) {
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 24),
                              child: CircularProgressIndicator());
                          }
                          if (state is AuthError) {
                            return Column(children: [
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: Colors.red[50],
                                  borderRadius: BorderRadius.circular(8)),
                                child: Text(localizeError(context, state.message),
                                    style: TextStyle(color: Colors.red[700], fontSize: 13),
                                    textAlign: TextAlign.center)),
                              const SizedBox(height: 16),
                              const PhoneLoginPage(),
                            ]);
                          }
                          return const PhoneLoginPage();
                        },
                      ),

                      const SizedBox(height: 24),

                      // Divider
                      Row(children: [
                        Expanded(child: Divider(color: Colors.grey[300])),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text(l.loginOr, style: TextStyle(color: Colors.grey[400], fontSize: 13))),
                        Expanded(child: Divider(color: Colors.grey[300])),
                      ]),

                      const SizedBox(height: 16),

                      // Telegram auth (secondary)
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _openTelegramLogin,
                          icon: const Icon(Icons.telegram, size: 20),
                          label: Text(l.loginViaTelegram),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(0, 48),
                            foregroundColor: AppColors.telegram,
                            side: const BorderSide(color: AppColors.telegram)),
                        ),
                      ),

                      const SizedBox(height: 24),
                      Text(l.loginFooter,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[500]),
                          textAlign: TextAlign.center),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
            ],
          ),
        ),
      ),
    );
  }
}
