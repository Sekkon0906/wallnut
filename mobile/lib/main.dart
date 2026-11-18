import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'api.dart';
import 'campus.dart';
import 'community.dart';
import 'models.dart';
import 'ui.dart';
import 'wallet.dart';

void main() => runApp(const WallnutApp());

class WallnutApp extends StatefulWidget {
  const WallnutApp({super.key, this.api});

  final WallnutApi? api;

  @override
  State<WallnutApp> createState() => _WallnutAppState();
}

class _WallnutAppState extends State<WallnutApp> {
  late final _api = (widget.api ?? WallnutApi())
    ..onSessionExpired = _clearSession;
  Member? _member;

  void _clearSession() {
    if (!mounted || _member == null) return;
    final navigator = _navigatorKey.currentState;
    navigator?.popUntil((route) => route.isFirst);
    setState(() => _member = null);
  }

  final _navigatorKey = GlobalKey<NavigatorState>();

  @override
  void dispose() {
    _api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = ColorScheme.fromSeed(seedColor: plum).copyWith(
      primary: plum,
      surface: paper,
      onSurface: ink,
      secondaryContainer: lilac,
      onSecondaryContainer: ink,
    );

    return MaterialApp(
      title: 'Wallnut',
      navigatorKey: _navigatorKey,
      locale: const Locale('es', 'CO'),
      supportedLocales: const [Locale('es', 'CO')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: colors,
        scaffoldBackgroundColor: paper,
        appBarTheme: const AppBarTheme(
          backgroundColor: paper,
          foregroundColor: ink,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFD7D0E4)),
          ),
        ),
        navigationBarTheme: const NavigationBarThemeData(
          backgroundColor: Colors.white,
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(minimumSize: const Size(0, 50)),
        ),
      ),
      home: switch (_member) {
        final member? => Home(
          api: _api,
          member: member,
          onLogout: _clearSession,
        ),
        null => SignIn(
          api: _api,
          onSignIn: (member) => setState(() => _member = member),
        ),
      },
    );
  }
}

class SignIn extends StatefulWidget {
  const SignIn({super.key, required this.api, required this.onSignIn});

  final WallnutApi api;
  final ValueChanged<Member> onSignIn;

  @override
  State<SignIn> createState() => _SignInState();
}

class _SignInState extends State<SignIn> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _signIn() async {
    if (_busy) return;
    if (_email.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Ingresa tu correo y contraseña.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final member = await widget.api.login(_email.text.trim(), _password.text);
      if (mounted) widget.onSignIn(member);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(26),
            children: [
              const Align(alignment: Alignment.centerLeft, child: BrandMark()),
              const SizedBox(height: 28),
              const Text(
                'Wallnut',
                style: TextStyle(
                  fontSize: 52,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -3,
                ),
              ),
              const Text(
                'Actividades y puntos del campus',
                style: TextStyle(fontSize: 17),
              ),
              const SizedBox(height: 34),
              TextField(
                controller: _email,
                enabled: !_busy,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.username],
                decoration: const InputDecoration(labelText: 'Correo'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _password,
                enabled: !_busy,
                obscureText: true,
                autofillHints: const [AutofillHints.password],
                decoration: const InputDecoration(labelText: 'Contraseña'),
                onSubmitted: (_) => _signIn(),
              ),
              if (_error case final error?)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    error,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _busy ? null : _signIn,
                child: Text(_busy ? 'Entrando…' : 'Iniciar sesión'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 54});
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: plum,
      borderRadius: BorderRadius.circular(size * .34),
    ),
    child: Icon(Icons.eco_outlined, color: Colors.white, size: size * .55),
  );
}

class Home extends StatefulWidget {
  const Home({
    super.key,
    required this.api,
    required this.member,
    required this.onLogout,
  });

  final WallnutApi api;
  final Member member;
  final VoidCallback onLogout;

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _tab = 0;
  bool _loggingOut = false;

  Future<void> _logout() async {
    setState(() => _loggingOut = true);
    try {
      await widget.api.logout();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) widget.onLogout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = widget.api;
    final member = widget.member;
    final page = switch (_tab) {
      0 => CampusPage(api: api, member: member),
      1 => WalletPage(api: api, member: member),
      2 => RankingPage(api: api, member: member),
      _ => ArdiPage(api: api),
    };
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            BrandMark(size: 34),
            SizedBox(width: 10),
            Text(
              'Wallnut',
              style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: -.6),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _loggingOut ? null : _logout,
            icon: const Icon(Icons.logout_outlined),
            tooltip: 'Cerrar sesión',
          ),
        ],
      ),
      body: SafeArea(top: false, bottom: false, child: page),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (tab) => setState(() => _tab = tab),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.event_outlined),
            label: 'Campus',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_wallet_outlined),
            label: 'Billetera',
          ),
          NavigationDestination(
            icon: Icon(Icons.emoji_events_outlined),
            label: 'Ranking',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            label: 'Ardi',
          ),
        ],
      ),
    );
  }
}
