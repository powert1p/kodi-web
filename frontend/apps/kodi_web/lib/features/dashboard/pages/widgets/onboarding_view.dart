import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:kodi_core/kodi_core.dart';
import '../../../../app/colors.dart';
import '../../../../shared/utils/responsive.dart';
import '../../bloc/dashboard_bloc.dart';
import '../../../diagnostic/pages/diagnostic_page.dart';
import '../../../exam/pages/exam_page.dart';
import '../../../practice/pages/practice_page.dart';

class OnboardingView extends StatelessWidget {
  const OnboardingView({super.key, required this.student});
  final Student student;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: EdgeInsets.all(rp(context, 24)),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: Column(
            children: [
              const SizedBox(height: 40),
              Container(
                width: rs(context, 100),
                height: rs(context, 100),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                      colors: [AppColors.gradientPurpleStart, AppColors.gradientPurpleEnd]),
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Icon(Icons.school_rounded,
                    color: Colors.white, size: rs(context, 52)),
              ),
              const SizedBox(height: 28),
              Text(
                'Привет, ${student.displayName.split(' ').first}! 👋',
                style: TextStyle(
                    fontSize: rs(context, 26),
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                'Добро пожаловать в NIS Math!\n'
                'Здесь ты подготовишься к экзамену по математике в НИШ.',
                style: TextStyle(
                    fontSize: rs(context, 16), color: Colors.grey[600], height: 1.5),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              // Step cards
              StepCard(
                number: '1',
                title: 'Пройди диагностику',
                subtitle: '5-10 минут · система определит твой уровень',
                icon: Icons.psychology_rounded,
                color: AppColors.purple,
              ),
              const SizedBox(height: 12),
              StepCard(
                number: '2',
                title: 'Узнай свои пробелы',
                subtitle: 'AI покажет где у тебя слабые места',
                icon: Icons.analytics_rounded,
                color: AppColors.primary,
              ),
              const SizedBox(height: 12),
              StepCard(
                number: '3',
                title: 'Тренируйся по темам',
                subtitle: '2525 задач с решениями и картинками',
                icon: Icons.fitness_center_rounded,
                color: AppColors.success,
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () => Navigator.of(context)
                      .pushNamed(DiagnosticPage.routeName)
                      .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Начать диагностику',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.w700)),
                  style: FilledButton.styleFrom(
                      minimumSize: const Size(0, 56),
                      backgroundColor: AppColors.purple),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.of(context)
                      .pushNamed(ExamPage.routeName)
                      .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                  icon: const Icon(Icons.timer_rounded, color: AppColors.error),
                  label: const Text('Экзамен с таймером',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                  style: OutlinedButton.styleFrom(
                      minimumSize: const Size(0, 48),
                      side: const BorderSide(color: AppColors.error)),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.of(context)
                    .pushNamed(PracticePage.routeName)
                    .then((_) => context.read<DashboardBloc>().add(DashboardLoad())),
                child: Text('Или просто порешать задачи →',
                    style: TextStyle(
                        color: Colors.grey[500], fontSize: 14)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StepCard extends StatelessWidget {
  const StepCard({
    super.key,
    required this.number,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
  });
  final String number, title, subtitle;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.all(rp(context, 16)),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withValues(alpha: 0.04),
                blurRadius: 6,
                offset: const Offset(0, 2)),
          ],
        ),
        child: Row(children: [
          Container(
            width: rs(context, 44),
            height: rs(context, 44),
            decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, color: color, size: rs(context, 24)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: TextStyle(
                        fontWeight: FontWeight.w600, fontSize: rs(context, 15))),
                Text(subtitle,
                    style: TextStyle(
                        fontSize: rs(context, 12), color: Colors.grey[500])),
              ],
            ),
          ),
        ]),
      );
}
