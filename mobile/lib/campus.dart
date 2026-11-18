import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'api.dart';
import 'models.dart';
import 'ui.dart';

class CampusPage extends StatelessWidget {
  const CampusPage({super.key, required this.api, required this.member});

  final WallnutApi api;
  final Member member;

  @override
  Widget build(BuildContext context) => FeatureList<List<Activity>>(
    load: api.activities,
    buildItems: (activities, reload) => [
      Panel(
        color: lilac,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Hola, ${member.displayName}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'Campus',
                    style: TextStyle(
                      fontSize: 38,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1.6,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.local_activity_outlined, size: 48, color: plum),
          ],
        ),
      ),
      const SizedBox(height: 24),
      const Heading('Actividades disponibles'),
      const SizedBox(height: 10),
      if (activities.isEmpty)
        const Panel(child: Text('Aún no hay actividades programadas.')),
      for (final activity in activities)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Panel(
            onTap: () async {
              await Navigator.of(context).push<void>(
                MaterialPageRoute(
                  builder: (_) => ActivityDetails(
                    api: api,
                    activity: activity,
                    member: member,
                  ),
                ),
              );
              if (context.mounted) reload();
            },
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: activity.inProgress ? mint : lilac,
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: Icon(
                    activity.inProgress
                        ? Icons.event_available
                        : Icons.calendar_today_outlined,
                    color: ink,
                  ),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        activity.title,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        activity.inProgress
                            ? 'En curso · ${activity.location}'
                            : '${formatDate(activity.startsAt)} · ${activity.location}',
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  activity.attended
                      ? 'Asististe'
                      : '+${formatPoints(activity.reward)} pts',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
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

class ActivityDetails extends StatefulWidget {
  const ActivityDetails({
    super.key,
    required this.api,
    required this.activity,
    required this.member,
  });

  final WallnutApi api;
  final Activity activity;
  final Member member;

  @override
  State<ActivityDetails> createState() => _ActivityDetailsState();
}

class _ActivityDetailsState extends State<ActivityDetails> {
  bool _busy = false;
  late bool _attended = widget.activity.attended;
  CheckinCode? _code;
  String? _error;
  String? _notice;

  Future<void> _issueCode() => _perform(() async {
    final code = await widget.api.issueCode(widget.activity.id);
    if (mounted) setState(() => _code = code);
  });

  Future<void> _scan() async {
    final code = await Navigator.of(context)
        .push<String>(MaterialPageRoute(builder: (_) => const ScannerPage()));
    if (mounted && code != null) await _attend(code);
  }

  Future<void> _pasteCode() async {
    final code = await showDialog<String>(
      context: context,
      builder: (_) => const CodeEntry(),
    );
    if (mounted && code != null) await _attend(code);
  }

  Future<void> _attend(String code) => _perform(() async {
    final attendance = await widget.api.attend(widget.activity.id, code);
    if (mounted) {
      setState(() {
        _attended = true;
        _notice = attendance.alreadyRecorded
            ? 'Tu asistencia ya estaba registrada.'
            : 'Asistencia registrada. Ganaste ${formatPoints(attendance.points)} puntos.';
      });
    }
  });

  Future<void> _perform(Future<void> Function() work) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await work();
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final activity = widget.activity;
    return Scaffold(
      appBar: AppBar(title: const Text('Actividad')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Panel(
              color: lilac,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    activity.title,
                    style: const TextStyle(
                      fontSize: 32,
                      height: 1.1,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '+${formatPoints(activity.reward)} puntos por asistencia',
                    style: const TextStyle(
                      color: moss,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            Text(activity.description, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 20),
            Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    activity.location,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 5),
                  Text('Inicio · ${formatDate(activity.startsAt)}'),
                  Text('Cierre · ${formatDate(activity.endsAt)}'),
                  const SizedBox(height: 8),
                  Text('Organiza ${activity.organizer}'),
                ],
              ),
            ),
            const SizedBox(height: 20),
            if (_attended)
              Panel(
                color: mint,
                child: Text(_notice ?? 'Ya registraste tu asistencia.'),
              )
            else if (activity.inProgress && activity.canIssueCode)
              FilledButton.icon(
                onPressed: _busy ? null : _issueCode,
                icon: const Icon(Icons.qr_code),
                label: Text(
                  _code == null ? 'Generar QR de asistencia' : 'Renovar QR',
                ),
              )
            else if (activity.inProgress && !widget.member.isOrganizer) ...[
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Escanear QR de asistencia'),
              ),
              TextButton(
                onPressed: _busy ? null : _pasteCode,
                child: const Text('Ingresar código manualmente'),
              ),
            ] else if (!activity.inProgress)
              const Text(
                'El registro de asistencia abre cuando comienza la actividad.',
              ),
            if (_code case final code?) ...[
              const SizedBox(height: 12),
              Panel(
                child: Column(
                  children: [
                    QrImageView(
                      data: code.code,
                      semanticsLabel: 'QR de asistencia',
                      size: 200,
                    ),
                    Text('Vence a las ${formatTime(code.expiresAt)}'),
                    const SizedBox(height: 8),
                    SelectableText(code.code, textAlign: TextAlign.center),
                  ],
                ),
              ),
            ],
            if (_busy) const LinearProgressIndicator(),
            if (_error case final error?)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  error,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  bool _detected = false;
  final _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Escanear asistencia')),
    body: MobileScanner(
      controller: _controller,
      errorBuilder: (context, error) => const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'No pudimos abrir la cámara. Revisa los permisos o ingresa el código manualmente.',
            textAlign: TextAlign.center,
          ),
        ),
      ),
      onDetect: (capture) {
        if (_detected) return;
        for (final barcode in capture.barcodes) {
          final code = barcode.rawValue;
          if (code == null || code.length < 20 || code.length > 100) continue;
          _detected = true;
          Navigator.of(context).pop(code);
          return;
        }
      },
    ),
  );
}

class CodeEntry extends StatefulWidget {
  const CodeEntry({super.key});

  @override
  State<CodeEntry> createState() => _CodeEntryState();
}

class _CodeEntryState extends State<CodeEntry> {
  final _text = TextEditingController();
  String? _error;

  void _submit() {
    final code = _text.text.trim();
    if (code.length < 20 || code.length > 100) {
      setState(() => _error = 'Ingresa el código del organizador.');
      return;
    }
    Navigator.of(context).pop(code);
  }

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Código de asistencia'),
    content: TextField(
      controller: _text,
      autofocus: true,
      autocorrect: false,
      textInputAction: TextInputAction.done,
      decoration: InputDecoration(labelText: 'Código', errorText: _error),
      onSubmitted: (_) => _submit(),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: const Text('Cancelar'),
      ),
      FilledButton(onPressed: _submit, child: const Text('Registrar')),
    ],
  );
}
