import 'package:flutter/material.dart';

import 'api.dart';
import 'models.dart';
import 'ui.dart';

class RankingPage extends StatelessWidget {
  const RankingPage({super.key, required this.api, required this.member});

  final WallnutApi api;
  final Member member;

  @override
  Widget build(BuildContext context) => FeatureList<List<RankEntry>>(
    load: api.ranking,
    buildItems: (ranking, _) => [
      const Panel(
        color: mint,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.emoji_events_outlined, size: 32, color: moss),
            SizedBox(height: 8),
            Heading('Ranking de participación'),
            SizedBox(height: 4),
            Text('Cuenta los puntos que ganas al asistir a actividades.'),
          ],
        ),
      ),
      const SizedBox(height: 16),
      if (ranking.isEmpty)
        const Panel(
          child: Text('El ranking se abrirá con la primera asistencia.'),
        ),
      for (final entry in ranking)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Panel(
            color: entry.handle == member.handle ? lilac : Colors.white,
            child: Row(
              children: [
                CircleAvatar(
                  backgroundColor: lilac,
                  foregroundColor: ink,
                  child: FittedBox(
                    child: Text(
                      '${entry.position}',
                      style: const TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.displayName,
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      Text('@${entry.handle}'),
                    ],
                  ),
                ),
                Text(
                  '${formatPoints(entry.points)} pts',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    color: moss,
                  ),
                ),
              ],
            ),
          ),
        ),
    ],
  );
}

class ArdiPage extends StatefulWidget {
  const ArdiPage({super.key, required this.api});

  final WallnutApi api;

  @override
  State<ArdiPage> createState() => _ArdiPageState();
}

class _ArdiPageState extends State<ArdiPage> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _messages = <({String text, bool fromUser})>[];
  bool _busy = false;
  String? _failedMessage;
  String? _error;

  Future<void> _ask(String value, {bool retry = false}) async {
    final message = value.trim();
    if (_busy || message.isEmpty) return;
    setState(() {
      _busy = true;
      _error = null;
      _failedMessage = null;
      if (!retry) {
        _messages.add((text: message, fromUser: true));
        _input.clear();
      }
    });
    _showLatest();
    try {
      final answer = await widget.api.askArdi(message);
      if (mounted)
        setState(() => _messages.add((text: answer, fromUser: false)));
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _failedMessage = message;
        });
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
        _showLatest();
      }
    }
  }

  void _showLatest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Expanded(
        child: ListView(
          controller: _scroll,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          children: [
            const Panel(
              color: lilac,
              child: Row(
                children: [
                  Icon(Icons.chat_bubble_outline, color: plum, size: 32),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Heading('Ardi'),
                        Text('Pregúntame por el campus y tus puntos.'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            if (_messages.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Wrap(
                  spacing: 6,
                  children: [
                    for (final prompt in [
                      '¿Qué actividades hay?',
                      '¿Cómo gano puntos?',
                      '¿Cómo funciona el ranking?',
                    ])
                      ActionChip(
                        label: Text(prompt),
                        onPressed: () => _ask(prompt),
                      ),
                  ],
                ),
              ),
            for (final message in _messages)
              Align(
                alignment: message.fromUser
                    ? Alignment.centerRight
                    : Alignment.centerLeft,
                child: Padding(
                  padding: EdgeInsets.only(
                    top: 10,
                    left: message.fromUser ? 28 : 0,
                    right: message.fromUser ? 0 : 28,
                  ),
                  child: Panel(
                    color: message.fromUser ? lilac : Colors.white,
                    child: Text(message.text),
                  ),
                ),
              ),
            if (_busy) const LinearProgressIndicator(),
            if (_error case final error?)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  error,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (_failedMessage case final message?)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: () => _ask(message, retry: true),
                  child: const Text('Reintentar'),
                ),
              ),
          ],
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _input,
                maxLength: 300,
                decoration: const InputDecoration(
                  hintText: 'Escribe una pregunta',
                  counterText: '',
                ),
                textInputAction: TextInputAction.send,
                onSubmitted: _ask,
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _busy ? null : () => _ask(_input.text),
              icon: const Icon(Icons.send_outlined),
              tooltip: 'Enviar pregunta',
            ),
          ],
        ),
      ),
    ],
  );
}
