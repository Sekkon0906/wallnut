import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

const ink = Color(0xFF231C36);
const plum = Color(0xFF5C3DB4);
const paper = Color(0xFFFAF8FE);
const lilac = Color(0xFFECE5FF);
const mint = Color(0xFFCFEDDA);
const moss = Color(0xFF1A633E);

String formatPoints(int value) =>
    NumberFormat.decimalPattern('es_CO').format(value);
String formatDate(DateTime value) =>
    DateFormat("d MMM · h:mm a", 'es_CO').format(value);
String formatTime(DateTime value) =>
    DateFormat('h:mm:ss a', 'es_CO').format(value);

class FeatureList<T> extends StatefulWidget {
  const FeatureList({super.key, required this.load, required this.buildItems});

  final Future<T> Function() load;
  final List<Widget> Function(T data, VoidCallback reload) buildItems;

  @override
  State<FeatureList<T>> createState() => _FeatureListState<T>();
}

class _FeatureListState<T> extends State<FeatureList<T>> {
  late Future<T> _result = widget.load();

  Future<void> _reload() async {
    final next = widget.load();
    setState(() => _result = next);
    try {
      await next;
    } on Exception {
      // FutureBuilder displays the error and retry action.
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
    future: _result,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(snapshot.error.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: _reload,
                  child: const Text('Reintentar'),
                ),
              ],
            ),
          ),
        );
      }
      return RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          physics: const AlwaysScrollableScrollPhysics(),
          children: widget.buildItems(snapshot.data as T, _reload),
        ),
      );
    },
  );
}

class Panel extends StatelessWidget {
  const Panel({
    super.key,
    required this.child,
    this.color = Colors.white,
    this.onTap,
  });
  final Widget child;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: color,
    borderRadius: BorderRadius.circular(22),
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(padding: const EdgeInsets.all(18), child: child),
    ),
  );
}

class Heading extends StatelessWidget {
  const Heading(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: Theme.of(context).textTheme.titleLarge
        ?.copyWith(fontWeight: FontWeight.w800),
  );
}
