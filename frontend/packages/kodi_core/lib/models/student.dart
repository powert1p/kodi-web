import 'package:equatable/equatable.dart';

class Student extends Equatable {
  const Student({
    required this.id,
    this.firstName,
    this.lastName,
    this.username,
    this.fullName,
    required this.lang,
    required this.registered,
    required this.diagnosticComplete,
    this.hasPausedDiagnostic = false,
  });

  final int id;
  final String? firstName;
  final String? lastName;
  final String? username;
  final String? fullName;
  final String lang;
  final bool registered;
  final bool diagnosticComplete;
  final bool hasPausedDiagnostic;

  String get displayName =>
      fullName ?? firstName ?? username ?? 'Ученик';

  factory Student.fromJson(Map<String, dynamic> json) => Student(
        id: json['id'] as int,
        firstName: json['first_name'] as String?,
        lastName: json['last_name'] as String?,
        username: json['username'] as String?,
        fullName: json['full_name'] as String?,
        lang: json['lang'] as String? ?? 'ru',
        registered: json['registered'] as bool? ?? false,
        diagnosticComplete:
            json['diagnostic_complete'] as bool? ?? false,
        hasPausedDiagnostic:
            json['has_paused_diagnostic'] as bool? ?? false,
      );

  @override
  List<Object?> get props => [id, lang, registered, diagnosticComplete, hasPausedDiagnostic];
}
