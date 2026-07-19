import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import '../data/local_unlock_store.dart';

class UnlockScreen extends ConsumerStatefulWidget {
  const UnlockScreen({super.key});

  @override
  ConsumerState<UnlockScreen> createState() => _UnlockScreenState();
}

class _UnlockScreenState extends ConsumerState<UnlockScreen> {
  final _pin = StringBuffer();
  var _error = false;
  var _busy = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(_tryBiometric);
  }

  Future<void> _tryBiometric() async {
    final config = ref.read(unlockConfigProvider);
    if (config?.method != UnlockMethod.biometric) return;
    await _authenticateBiometric();
  }

  Future<void> _authenticateBiometric() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final auth = LocalAuthentication();
      final canCheck = await auth.canCheckBiometrics || await auth.isDeviceSupported();
      if (!canCheck) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Биометрия недоступна на этом устройстве')),
          );
        }
        return;
      }
      final ok = await auth.authenticate(
        localizedReason: 'Разблокируйте Berrio',
        biometricOnly: false,
        persistAcrossBackgrounding: true,
      );
      if (ok && mounted) {
        ref.read(sessionUnlockedProvider.notifier).state = true;
      }
    } on LocalAuthException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.description ?? 'Ошибка биометрии')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _onDigit(String d) async {
    if (_pin.length >= 4) return;
    setState(() {
      _error = false;
      _pin.write(d);
    });
    if (_pin.length < 4) return;
    final store = ref.read(localUnlockStoreProvider);
    final ok = await store.verifyPin(_pin.toString());
    if (!mounted) return;
    if (ok) {
      ref.read(sessionUnlockedProvider.notifier).state = true;
    } else {
      setState(() {
        _error = true;
        _pin.clear();
      });
    }
  }

  void _onBackspace() {
    if (_pin.isEmpty) return;
    final s = _pin.toString();
    _pin.clear();
    _pin.write(s.substring(0, s.length - 1));
    setState(() => _error = false);
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(unlockConfigProvider);
    final scheme = Theme.of(context).colorScheme;
    final isPin = config?.method == UnlockMethod.pin;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),
              Text(
                'Berrio',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: scheme.primary,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                isPin ? 'Введите PIN' : 'Быстрый вход',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              if (_error) ...[
                const SizedBox(height: 8),
                Text(
                  'Неверный PIN',
                  style: TextStyle(color: scheme.error),
                ),
              ],
              if (isPin) ...[
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(4, (i) {
                    final filled = i < _pin.length;
                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      width: 14,
                      height: 14,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: filled
                            ? scheme.primary
                            : scheme.outline.withValues(alpha: 0.35),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 32),
                _PinPad(onDigit: _onDigit, onBackspace: _onBackspace),
              ] else ...[
                const SizedBox(height: 32),
                FilledButton.icon(
                  onPressed: _busy ? null : _authenticateBiometric,
                  icon: const Icon(Icons.fingerprint),
                  label: const Text('Разблокировать'),
                ),
              ],
              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }
}

class _PinPad extends StatelessWidget {
  const _PinPad({required this.onDigit, required this.onBackspace});

  final ValueChanged<String> onDigit;
  final VoidCallback onBackspace;

  @override
  Widget build(BuildContext context) {
    final keys = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', '⌫'],
    ];
    return Column(
      children: keys.map((row) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: row.map((k) {
              if (k.isEmpty) return const SizedBox(width: 72, height: 56);
              if (k == '⌫') {
                return SizedBox(
                  width: 72,
                  height: 56,
                  child: IconButton(
                    onPressed: onBackspace,
                    icon: const Icon(Icons.backspace_outlined),
                  ),
                );
              }
              return SizedBox(
                width: 72,
                height: 56,
                child: FilledButton.tonal(
                  onPressed: () => onDigit(k),
                  child: Text(k, style: const TextStyle(fontSize: 22)),
                ),
              );
            }).toList(),
          ),
        );
      }).toList(),
    );
  }
}

/// Dialog after login/register: offer biometric / PIN / skip.
Future<void> offerQuickUnlockDialog(BuildContext context, WidgetRef ref) async {
  final choice = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Включить быстрый вход?'),
      content: const Text(
        'Разблокируйте приложение биометрией или PIN. '
        'Пароль аккаунта при этом не сохраняется.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, 'skip'),
          child: const Text('Пропустить'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(ctx, 'pin'),
          child: const Text('PIN'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(ctx, 'biometric'),
          child: const Text('Биометрия'),
        ),
      ],
    ),
  );

  if (!context.mounted || choice == null || choice == 'skip') {
    ref.read(sessionUnlockedProvider.notifier).state = true;
    return;
  }

  final store = ref.read(localUnlockStoreProvider);
  if (choice == 'biometric') {
    final auth = LocalAuthentication();
    try {
      final can = await auth.canCheckBiometrics || await auth.isDeviceSupported();
      if (!can) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Биометрия недоступна')),
          );
        }
        ref.read(sessionUnlockedProvider.notifier).state = true;
        return;
      }
      final ok = await auth.authenticate(
        localizedReason: 'Подтвердите для быстрого входа',
        biometricOnly: false,
        persistAcrossBackgrounding: true,
      );
      if (ok) {
        await store.enableBiometric();
        ref.read(unlockConfigProvider.notifier).state =
            const UnlockConfig(enabled: true, method: UnlockMethod.biometric);
      }
    } catch (_) {
      // Fall through — still unlock session.
    }
    ref.read(sessionUnlockedProvider.notifier).state = true;
    return;
  }

  if (choice == 'pin') {
    final pin = await _askPin(context);
    if (pin != null && pin.length == 4) {
      await store.enablePin(pin);
      ref.read(unlockConfigProvider.notifier).state =
          const UnlockConfig(enabled: true, method: UnlockMethod.pin);
    }
    ref.read(sessionUnlockedProvider.notifier).state = true;
  }
}

Future<String?> _askPin(BuildContext context) async {
  final ctrl = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Задайте PIN (4 цифры)'),
      content: TextField(
        controller: ctrl,
        keyboardType: TextInputType.number,
        obscureText: true,
        maxLength: 4,
        decoration: const InputDecoration(
          labelText: 'PIN',
          border: OutlineInputBorder(),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Отмена')),
        FilledButton(
          onPressed: () {
            final v = ctrl.text.trim();
            if (v.length != 4 || int.tryParse(v) == null) return;
            Navigator.pop(ctx, v);
          },
          child: const Text('Сохранить'),
        ),
      ],
    ),
  );
}
