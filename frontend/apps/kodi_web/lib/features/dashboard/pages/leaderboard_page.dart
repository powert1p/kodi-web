import 'package:flutter/material.dart';
import '../bloc/dashboard_bloc.dart';

enum LeaderboardSort { byQuantity, byAccuracy, byProgress }

class LeaderboardPage extends StatefulWidget {
  const LeaderboardPage({super.key, required this.entries});
  final List<LeaderboardEntry> entries;
  static const routeName = '/leaderboard';

  @override
  State<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends State<LeaderboardPage> {
  LeaderboardSort _sort = LeaderboardSort.byQuantity;

  List<LeaderboardEntry> get _sorted {
    final list = List<LeaderboardEntry>.from(widget.entries);
    switch (_sort) {
      case LeaderboardSort.byQuantity:
        list.sort((a, b) => b.solved.compareTo(a.solved));
      case LeaderboardSort.byAccuracy:
        list.sort((a, b) => b.accuracy.compareTo(a.accuracy));
      case LeaderboardSort.byProgress:
        list.sort((a, b) => b.mastered.compareTo(a.mastered));
    }
    return list;
  }

  String _sortLabel(LeaderboardSort s) => switch (s) {
        LeaderboardSort.byQuantity => 'По количеству',
        LeaderboardSort.byAccuracy => 'По точности',
        LeaderboardSort.byProgress => 'По прогрессу',
      };

  String _valueForSort(LeaderboardEntry e) => switch (_sort) {
        LeaderboardSort.byQuantity => '${e.solved}',
        LeaderboardSort.byAccuracy => '${e.accuracy}%',
        LeaderboardSort.byProgress => '${e.mastered}',
      };

  @override
  Widget build(BuildContext context) {
    final sorted = _sorted;

    return Scaffold(
      backgroundColor: const Color(0xFFFAF9F6),
      appBar: AppBar(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
        elevation: 0.5,
        leading: const BackButton(),
        title: const Text('🏆 Лидерборд',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
            children: [
              // Sort tabs
              Container(
                color: Colors.white,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Row(
                  children: LeaderboardSort.values.map((s) {
                    final active = _sort == s;
                    return Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _sort = s),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          decoration: BoxDecoration(
                            color: active
                                ? const Color(0xFFFFF3E0)
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            _sortLabel(s),
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight:
                                  active ? FontWeight.w700 : FontWeight.w500,
                              color: active
                                  ? const Color(0xFFE65100)
                                  : Colors.grey[600],
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const Divider(height: 1),

              // List
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: sorted.length,
                  itemBuilder: (context, i) {
                    final e = sorted[i];
                    final rank = i + 1;
                    return _LeaderboardRow(
                      rank: rank,
                      entry: e,
                      value: _valueForSort(e),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.rank,
    required this.entry,
    required this.value,
  });

  final int rank;
  final LeaderboardEntry entry;
  final String value;

  String get _medal => switch (rank) {
        1 => '🥇',
        2 => '🥈',
        3 => '🥉',
        _ => '$rank',
      };

  @override
  Widget build(BuildContext context) {
    final isCurrent = entry.isCurrent;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: isCurrent ? const Color(0xFFFFF8E1) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: isCurrent
            ? Border.all(color: const Color(0xFFFFB300), width: 1.5)
            : null,
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 4,
              offset: const Offset(0, 1)),
        ],
      ),
      child: Row(
        children: [
          // Rank
          SizedBox(
            width: 36,
            child: Text(
              _medal,
              style: TextStyle(
                fontSize: rank <= 3 ? 22 : 16,
                fontWeight: FontWeight.bold,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(width: 12),
          // Name
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.name,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight:
                        isCurrent ? FontWeight.w700 : FontWeight.w500,
                    color: const Color(0xFF1E293B),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                if (isCurrent)
                  Text('Это вы',
                      style: TextStyle(
                          fontSize: 11, color: Colors.orange[700])),
              ],
            ),
          ),
          // Value
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: isCurrent
                  ? const Color(0xFFE65100)
                  : const Color(0xFF1E293B),
            ),
          ),
        ],
      ),
    );
  }
}
