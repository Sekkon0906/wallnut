import 'package:flutter/material.dart';

import 'api.dart';
import 'models.dart';
import 'ui.dart';

class WalletPage extends StatelessWidget {
  const WalletPage({super.key, required this.api, required this.member});

  final WallnutApi api;
  final Member member;

  @override
  Widget build(BuildContext context) => FeatureList<Wallet>(
    load: api.wallet,
    buildItems: (wallet, reload) => [
      Panel(
        color: ink,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Saldo disponible',
              style: TextStyle(color: lilac, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Text(
              '${formatPoints(wallet.balance)} pts',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 38,
                fontWeight: FontWeight.w900,
                letterSpacing: -1,
              ),
            ),
            SelectableText(
              '@${member.handle}',
              style: const TextStyle(color: lilac),
            ),
          ],
        ),
      ),
      if (!member.isOrganizer) ...[
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: wallet.balance == 0
              ? null
              : () async {
                  final sent = await showDialog<bool>(
                    context: context,
                    barrierDismissible: false,
                    builder: (_) => TransferDialog(api: api),
                  );
                  if (!context.mounted) return;
                  reload();
                  if (sent == true) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Puntos enviados.')),
                    );
                  }
                },
          icon: const Icon(Icons.arrow_outward),
          label: const Text('Enviar puntos'),
        ),
      ],
      const SizedBox(height: 24),
      const Heading('Movimientos recientes'),
      const SizedBox(height: 10),
      if (wallet.movements.isEmpty)
        const Panel(
          child: Text('Los puntos que ganes o recibas aparecerán aquí.'),
        ),
      for (final movement in wallet.movements)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Panel(
            child: Row(
              children: [
                Icon(
                  movement.isAttendance
                      ? Icons.event_available
                      : Icons.sync_alt,
                  color: plum,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        movement.isAttendance
                            ? movement.label
                            : '@${movement.label}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      Text(formatDate(movement.createdAt)),
                    ],
                  ),
                ),
                Text(
                  '${movement.points > 0 ? '+' : ''}${formatPoints(movement.points)}',
                  style: TextStyle(
                    color: movement.points > 0 ? moss : ink,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
    ],
  );
}

class TransferDialog extends StatefulWidget {
  const TransferDialog({super.key, required this.api});

  final WallnutApi api;

  @override
  State<TransferDialog> createState() => _TransferDialogState();
}

class _TransferDialogState extends State<TransferDialog> {
  final _recipient = TextEditingController();
  final _points = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _submit() async {
    if (_busy) return;
    final recipient = _recipient.text.trim().toLowerCase().replaceFirst(
      RegExp(r'^@'),
      '',
    );
    final points = int.tryParse(_points.text.trim());
    if (!RegExp(r'^[a-z0-9_]{3,24}$').hasMatch(recipient) ||
        points == null ||
        points < 1 ||
        points > 1000000) {
      setState(
        () =>
            _error = 'Ingresa el @usuario y una cantidad entre 1 y 1.000.000.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.transfer(recipient, points);
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.status == null || error.status! >= 500
              ? '${error.message} Puedes reintentar con los mismos datos o consultar tu historial.'
              : error.message;
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _recipient.dispose();
    _points.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: AlertDialog(
      title: const Text('Enviar puntos'),
      scrollable: true,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _recipient,
            enabled: !_busy,
            autocorrect: false,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(labelText: '@usuario de destino'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _points,
            enabled: !_busy,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Cantidad'),
          ),
          if (_error case final error?)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Text(
                error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: Text(_busy ? 'Enviando…' : 'Enviar'),
        ),
      ],
    ),
  );
}
