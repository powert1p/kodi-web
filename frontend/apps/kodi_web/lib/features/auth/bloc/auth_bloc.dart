import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:kodi_core/kodi_core.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ── Events ────────────────────────────────────────────────────
abstract class AuthEvent extends Equatable {
  @override List<Object?> get props => [];
}

class AuthCheckRequested extends AuthEvent {}
class AuthTelegramLogin extends AuthEvent {
  AuthTelegramLogin(this.tgData);
  final Map<String, dynamic> tgData;
  @override List<Object?> get props => [tgData];
}
class AuthTokenReceived extends AuthEvent {
  AuthTokenReceived(this.token);
  final String token;
  @override List<Object?> get props => [token];
}
class AuthLogout extends AuthEvent {}

// ── States ────────────────────────────────────────────────────
abstract class AuthState extends Equatable {
  @override List<Object?> get props => [];
}
class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthAuthenticated extends AuthState {
  AuthAuthenticated(this.student);
  final Student student;
  @override List<Object?> get props => [student];
}
class AuthUnauthenticated extends AuthState {}
class AuthError extends AuthState {
  AuthError(this.message);
  final String message;
  @override List<Object?> get props => [message];
}

// ── Bloc ──────────────────────────────────────────────────────
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc({required this.api}) : super(AuthInitial()) {
    on<AuthCheckRequested>(_onCheck);
    on<AuthTelegramLogin>(_onTelegramLogin);
    on<AuthTokenReceived>(_onTokenReceived);
    on<AuthLogout>(_onLogout);
  }

  final NisApiClient api;
  static const _tokenKey = 'jwt_token';

  Future<void> _onCheck(
    AuthCheckRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString(_tokenKey);
      if (token == null) {
        emit(AuthUnauthenticated());
        return;
      }
      api.token = token;
      final student = await api.getMe();
      emit(AuthAuthenticated(student));
    } catch (e, st) {
      debugPrint('[AuthBloc._onCheck] $e\n$st');
      emit(AuthUnauthenticated());
    }
  }

  Future<void> _onTelegramLogin(
    AuthTelegramLogin event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    try {
      final token = await api.loginWithTelegram(event.tgData);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);
      final student = await api.getMe();
      emit(AuthAuthenticated(student));
    } on NetworkException catch (e) {
      emit(AuthError(e.message));
    } on ApiException catch (e) {
      emit(AuthError(e.userMessage));
    } catch (e, st) {
      debugPrint('[AuthBloc._onTelegramLogin] $e\n$st');
      emit(AuthError('Не удалось войти через Telegram. Попробуйте ещё раз.'));
    }
  }

  Future<void> _onTokenReceived(
    AuthTokenReceived event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    try {
      api.token = event.token;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, event.token);
      final student = await api.getMe();
      emit(AuthAuthenticated(student));
    } on NetworkException catch (e) {
      emit(AuthError(e.message));
    } on ApiException catch (e) {
      emit(AuthError(e.userMessage));
    } catch (e, st) {
      debugPrint('[AuthBloc._onTokenReceived] $e\n$st');
      emit(AuthError('Не удалось загрузить профиль. Попробуйте ещё раз.'));
    }
  }

  Future<void> _onLogout(
    AuthLogout event,
    Emitter<AuthState> emit,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    api.token = null;
    emit(AuthUnauthenticated());
  }
}
