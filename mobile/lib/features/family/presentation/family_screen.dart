import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/widgets/journey_state_panel.dart';
import '../data/families_api.dart';

class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(familiesListProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Family'),
        actions: [
          IconButton(
            tooltip: 'Accept invite',
            onPressed: () => _acceptInvite(context, ref),
            icon: const Icon(Icons.mail_outline),
          ),
          IconButton(
            onPressed: () => ref.invalidate(familiesListProvider),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _createFamily(context, ref),
        child: const Icon(Icons.add),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(familiesListProvider),
        ),
        data: (families) {
          if (families.isEmpty) {
            return JourneyStatePanel.empty(
              title: 'No family yet',
              message: 'Create a family space or accept an invite token.',
              actionLabel: 'Create family',
              onAction: () => _createFamily(context, ref),
            );
          }
          return ListView.separated(
            itemCount: families.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final f = families[index];
              return ListTile(
                title: Text(f.name),
                subtitle: Text('Owner ${f.ownerUserId.substring(0, 8)}…'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => FamilyDetailScreen(family: f),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _createFamily(BuildContext context, WidgetRef ref) async {
    final ctrl = TextEditingController(text: 'Семья');
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New family'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Create')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(familiesApiProvider).create(ctrl.text.trim());
    ref.invalidate(familiesListProvider);
  }

  Future<void> _acceptInvite(BuildContext context, WidgetRef ref) async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Accept invite'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: 'Invite token'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Join')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref.read(familiesApiProvider).acceptInvite(ctrl.text.trim());
      ref.invalidate(familiesListProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Joined family')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not accept: $e')),
        );
      }
    }
  }
}

class FamilyDetailScreen extends ConsumerStatefulWidget {
  const FamilyDetailScreen({super.key, required this.family});

  final FamilyDto family;

  @override
  ConsumerState<FamilyDetailScreen> createState() => _FamilyDetailScreenState();
}

class _FamilyDetailScreenState extends ConsumerState<FamilyDetailScreen> {
  List<MemberDto>? _members;
  List<InviteDto>? _invites;
  Object? _error;
  var _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(familiesApiProvider);
      final members = await api.members(widget.family.id);
      List<InviteDto> invites = const [];
      try {
        invites = await api.listInvites(widget.family.id);
      } catch (_) {
        // No invite permission — hide silently.
      }
      if (!mounted) return;
      setState(() {
        _members = members;
        _invites = invites;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  Future<void> _invite() async {
    final emailCtrl = TextEditingController();
    var role = 'PARENT';
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Invite member'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: emailCtrl,
                decoration: const InputDecoration(
                  labelText: 'Email (optional lock)',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: role,
                items: const [
                  DropdownMenuItem(value: 'PARENT', child: Text('Parent')),
                  DropdownMenuItem(value: 'CHILD', child: Text('Child')),
                ],
                onChanged: (v) => setLocal(() => role = v ?? 'PARENT'),
                decoration: const InputDecoration(labelText: 'Role'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Create')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final invite = await ref.read(familiesApiProvider).createInvite(
          familyId: widget.family.id,
          role: role,
          email: emailCtrl.text.trim().isEmpty ? null : emailCtrl.text.trim(),
        );
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Invite token'),
        content: SelectableText(
          invite.token ?? '(token unavailable)',
          style: const TextStyle(fontFamily: 'monospace'),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: invite.token ?? ''));
              Navigator.pop(context);
            },
            child: const Text('Copy & close'),
          ),
        ],
      ),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.family.name),
        actions: [
          IconButton(onPressed: _invite, icon: const Icon(Icons.person_add_alt_1)),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? JourneyStatePanel.error(message: '$_error', onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                  children: [
                    Text(
                      'Members',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 8),
                    ...?_members?.map(
                      (m) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(m.role),
                        subtitle: Text(m.userId),
                      ),
                    ),
                    if (_invites != null && _invites!.isNotEmpty) ...[
                      const SizedBox(height: 20),
                      Text(
                        'Invites',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      ..._invites!.map(
                        (i) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${i.role} · ${i.status}'),
                          subtitle: Text(
                            'Expires ${i.expiresAt.toLocal()}'
                            '${i.hasEmailLock ? ' · email-locked' : ''}',
                          ),
                          trailing: i.status == 'PENDING'
                              ? IconButton(
                                  icon: const Icon(Icons.close),
                                  onPressed: () async {
                                    await ref
                                        .read(familiesApiProvider)
                                        .revokeInvite(widget.family.id, i.id);
                                    await _load();
                                  },
                                )
                              : null,
                        ),
                      ),
                    ],
                  ],
                ),
    );
  }
}
