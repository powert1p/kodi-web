import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ── Events ──

sealed class LocaleEvent {}

class LocaleLoaded extends LocaleEvent {}

class LocaleChanged extends LocaleEvent {
  LocaleChanged(this.locale);
  final Locale locale;
}

// ── State ──

class LocaleState {
  const LocaleState(this.locale);
  final Locale locale;
}

// ── Bloc ──

class LocaleBloc extends Bloc<LocaleEvent, LocaleState> {
  LocaleBloc() : super(const LocaleState(Locale('ru'))) {
    on<LocaleLoaded>(_onLoaded);
    on<LocaleChanged>(_onChanged);
  }

  static const _key = 'app_lang';

  Future<void> _onLoaded(LocaleLoaded event, Emitter<LocaleState> emit) async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_key) ?? 'ru';
    emit(LocaleState(Locale(code)));
  }

  Future<void> _onChanged(LocaleChanged event, Emitter<LocaleState> emit) async {
    emit(LocaleState(event.locale));
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, event.locale.languageCode);
  }
}
