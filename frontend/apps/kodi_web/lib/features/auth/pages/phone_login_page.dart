import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../bloc/auth_bloc.dart';

class PhoneLoginPage extends StatefulWidget {
  const PhoneLoginPage({super.key});
  @override
  State<PhoneLoginPage> createState() => _PhoneLoginPageState();
}

class _PhoneLoginPageState extends State<PhoneLoginPage> {
  final _phoneController = TextEditingController(text: '+7');
  final _pinController = TextEditingController();
  final _nameController = TextEditingController();
  bool _isRegister = false;
  bool _phoneChecked = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _phoneController.dispose();
    _pinController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    final phone = _phoneController.text.trim();
    if (phone.length < 10) {
      setState(() => _error = 'Введите номер телефона');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final api = context.read<NisApiClient>();
      final exists = await api.checkPhone(phone);
      setState(() { _phoneChecked = true; _isRegister = !exists; _loading = false; });
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось проверить номер. Попробуйте ещё раз.'; });
    }
  }

  Future<void> _submit() async {
    final phone = _phoneController.text.trim();
    final pin = _pinController.text.trim();
    if (pin.length != 4) {
      setState(() => _error = 'PIN — 4 цифры');
      return;
    }
    if (_isRegister && _nameController.text.trim().isEmpty) {
      setState(() => _error = 'Введите имя');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final api = context.read<NisApiClient>();
      String jwt;
      if (_isRegister) {
        jwt = await api.phoneRegister(phone, _nameController.text.trim(), pin);
      } else {
        jwt = await api.phoneLogin(phone, pin);
      }
      if (!mounted) return;
      context.read<AuthBloc>().add(AuthTokenReceived(jwt));
    } on NetworkException catch (e) {
      setState(() { _loading = false; _error = e.message; });
    } on ApiException catch (e) {
      setState(() { _loading = false; _error = e.userMessage; });
    } catch (_) {
      setState(() { _loading = false; _error = 'Не удалось войти. Попробуйте ещё раз.'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Phone input
        TextField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          enabled: !_phoneChecked,
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[+0-9]'))],
          decoration: InputDecoration(
            labelText: 'Номер телефона',
            hintText: '+7 777 123 4567',
            prefixIcon: const Icon(Icons.phone_rounded),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            filled: true, fillColor: Colors.grey[50],
          ),
          style: const TextStyle(fontSize: 18, letterSpacing: 1),
          onSubmitted: !_phoneChecked ? (_) => _checkPhone() : null,
        ),

        if (!_phoneChecked) ...[
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _loading ? null : _checkPhone,
              style: FilledButton.styleFrom(
                minimumSize: const Size(0, 52),
                backgroundColor: const Color(0xFF2563EB)),
              child: _loading
                  ? const SizedBox(width: 22, height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Продолжить', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ),
        ],

        if (_phoneChecked) ...[
          const SizedBox(height: 12),
          if (_isRegister) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.blue[50], borderRadius: BorderRadius.circular(8)),
              child: Row(children: [
                Icon(Icons.info_outline, color: Colors.blue[400], size: 18),
                const SizedBox(width: 8),
                const Expanded(child: Text('Новый ученик! Заполни имя и придумай PIN',
                    style: TextStyle(fontSize: 13, color: Color(0xFF1E40AF)))),
              ]),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nameController,
              textCapitalization: TextCapitalization.words,
              decoration: InputDecoration(
                labelText: 'Имя',
                hintText: 'Как тебя зовут?',
                prefixIcon: const Icon(Icons.person_rounded),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                filled: true, fillColor: Colors.grey[50]),
            ),
            const SizedBox(height: 12),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.green[50], borderRadius: BorderRadius.circular(8)),
              child: Row(children: [
                Icon(Icons.check_circle_outline, color: Colors.green[400], size: 18),
                const SizedBox(width: 8),
                const Expanded(child: Text('Номер найден! Введи свой PIN',
                    style: TextStyle(fontSize: 13, color: Color(0xFF166534)))),
              ]),
            ),
            const SizedBox(height: 12),
          ],
          TextField(
            controller: _pinController,
            keyboardType: TextInputType.number,
            obscureText: true,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(4)],
            textAlign: TextAlign.center,
            autofocus: true,
            decoration: InputDecoration(
              labelText: _isRegister ? 'Придумай PIN (4 цифры)' : 'PIN-код',
              hintText: '••••',
              prefixIcon: const Icon(Icons.lock_rounded),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              filled: true, fillColor: Colors.grey[50]),
            style: const TextStyle(fontSize: 24, letterSpacing: 12),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _loading ? null : _submit,
              style: FilledButton.styleFrom(
                minimumSize: const Size(0, 52),
                backgroundColor: const Color(0xFF2563EB)),
              child: _loading
                  ? const SizedBox(width: 22, height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(_isRegister ? 'Зарегистрироваться' : 'Войти',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => setState(() { _phoneChecked = false; _pinController.clear(); _nameController.clear(); _error = null; }),
            child: const Text('Изменить номер'),
          ),
        ],

        if (_error != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.red[50], borderRadius: BorderRadius.circular(8)),
            child: Row(children: [
              Icon(Icons.error_outline, color: Colors.red[400], size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(_error!, style: TextStyle(color: Colors.red[700], fontSize: 13))),
            ]),
          ),
        ],
      ],
    );
  }
}
