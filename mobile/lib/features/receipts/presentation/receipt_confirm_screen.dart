import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../shared/refresh.dart';
import '../../../shared/widgets/journey_state_panel.dart';
import '../data/receipts_api.dart';

const _categoryOptions = <({String label, String slug})>[
  (label: 'Еда', slug: 'food'),
  (label: 'Транспорт', slug: 'transport'),
  (label: 'Дом', slug: 'home'),
  (label: 'Здоровье', slug: 'health'),
  (label: 'Развлечения', slug: 'entertainment'),
  (label: 'Подписки', slug: 'subscriptions'),
  (label: 'Покупки', slug: 'shopping'),
  (label: 'Одежда', slug: 'clothes'),
  (label: 'Другое', slug: 'other'),
];

String? categorySlugFromName(String? name) {
  if (name == null || name.trim().isEmpty) return null;
  final lower = name.trim().toLowerCase();
  for (final opt in _categoryOptions) {
    if (opt.slug == lower || opt.label.toLowerCase() == lower) return opt.slug;
  }
  if (lower.contains('продукт') || lower.contains('еда') || lower.contains('food')) {
    return 'food';
  }
  if (lower.contains('транспорт') || lower.contains('transport')) return 'transport';
  if (lower.contains('дом') || lower.contains('home')) return 'home';
  if (lower.contains('здоров') || lower.contains('health')) return 'health';
  if (lower.contains('развлеч') || lower.contains('entertainment')) {
    return 'entertainment';
  }
  if (lower.contains('подписк') || lower.contains('subscription')) {
    return 'subscriptions';
  }
  if (lower.contains('покуп') || lower.contains('shopping')) return 'shopping';
  if (lower.contains('одежд') || lower.contains('clothes')) return 'clothes';
  if (lower.contains('друг') || lower.contains('other')) return 'other';
  return null;
}

bool _isDateSuspicious(List<String> warnings) {
  return warnings.any((w) => w.toLowerCase().contains('проверьте дату'));
}

class _EditableItem {
  _EditableItem({
    required this.name,
    required this.qty,
    required this.price,
    required this.sum,
    this.categorySlug,
    this.nameDisplay,
  });

  factory _EditableItem.fromDto(ReceiptItemDto item) {
    final display = item.nameDisplay?.trim().isNotEmpty == true
        ? item.nameDisplay!
        : item.nameRaw;
    return _EditableItem(
      name: item.nameRaw,
      nameDisplay: display,
      qty: item.qty,
      price: item.price,
      sum: item.sum,
      categorySlug: categorySlugFromName(item.categoryName),
    );
  }

  String name;
  String qty;
  String price;
  String sum;
  String? categorySlug;
  String? nameDisplay;
}

class ReceiptConfirmScreen extends ConsumerStatefulWidget {
  const ReceiptConfirmScreen({super.key, required this.receiptId});

  final String receiptId;

  @override
  ConsumerState<ReceiptConfirmScreen> createState() =>
      _ReceiptConfirmScreenState();
}

class _ReceiptConfirmScreenState extends ConsumerState<ReceiptConfirmScreen> {
  final _storeController = TextEditingController();
  final _totalController = TextEditingController();
  DateTime? _purchasedAt;
  List<_EditableItem> _items = [];
  List<String> _warnings = [];
  var _loaded = false;
  var _saving = false;
  var _dateIgnored = false;
  var _dateConfirmed = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _storeController.dispose();
    _totalController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loadError = null;
      _loaded = false;
    });
    try {
      final receipt =
          await ref.read(receiptsApiProvider).getById(widget.receiptId);
      if (!mounted) return;
      _storeController.text = receipt.storeName ?? '';
      _totalController.text = receipt.totalAmount ?? '';
      setState(() {
        _purchasedAt = receipt.purchasedAt;
        _items = receipt.items.map(_EditableItem.fromDto).toList();
        _warnings = List<String>.from(receipt.warnings);
        _loaded = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadError = e.toString();
        _loaded = true;
      });
    }
  }

  Future<void> _pickDate() async {
    final initial = _purchasedAt?.toLocal() ?? DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2015),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (!mounted) return;
    final next = DateTime(
      date.year,
      date.month,
      date.day,
      time?.hour ?? initial.hour,
      time?.minute ?? initial.minute,
    );
    setState(() {
      _purchasedAt = next;
      _dateConfirmed = true;
      _dateIgnored = false;
    });
  }

  String _recalcSum(String qty, String price) {
    final q = double.tryParse(qty.replaceAll(',', '.')) ?? 0;
    final p = double.tryParse(price.replaceAll(',', '.')) ?? 0;
    return (q * p).toStringAsFixed(2);
  }

  ReceiptConfirmPayload _buildPayload({required bool saveAsDraft}) {
    return ReceiptConfirmPayload(
      storeName: _storeController.text.trim().isEmpty
          ? null
          : _storeController.text.trim(),
      totalAmount: _totalController.text.trim().isEmpty
          ? null
          : _totalController.text.trim().replaceAll(',', '.'),
      purchasedAt: _purchasedAt?.toUtc().toIso8601String(),
      items: _items
          .map(
            (i) => ReceiptConfirmItemPayload(
              name: i.name.trim().isEmpty ? (i.nameDisplay ?? '') : i.name,
              qty: i.qty.replaceAll(',', '.'),
              price: i.price.replaceAll(',', '.'),
              sum: i.sum.replaceAll(',', '.'),
              categorySlug: i.categorySlug,
              nameDisplay: i.nameDisplay,
            ),
          )
          .where((i) => i.name.trim().isNotEmpty)
          .toList(),
      saveAsDraft: saveAsDraft,
      dateIgnored: _dateIgnored,
      dateConfirmed: _dateConfirmed,
    );
  }

  Future<void> _submit({required bool saveAsDraft}) async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await ref.read(receiptsApiProvider).confirm(
            widget.receiptId,
            _buildPayload(saveAsDraft: saveAsDraft),
          );
      refreshMoneySurfaces(ref);
      ref.invalidate(receiptDetailProvider(widget.receiptId));
      ref.invalidate(receiptsListProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            saveAsDraft
                ? 'Черновик сохранён — можно исправить позже'
                : 'Чек сохранён',
          ),
        ),
      );
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/receipts/${widget.receiptId}');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Не удалось сохранить: $e')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (!_loaded) {
      return Scaffold(
        appBar: AppBar(title: const Text('Подтверждение чека')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_loadError != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Подтверждение чека')),
        body: JourneyStatePanel.error(
          message: _loadError!,
          onRetry: _load,
        ),
      );
    }

    final dateLabel = _purchasedAt != null
        ? DateFormat('d MMM yyyy, HH:mm').format(_purchasedAt!.toLocal())
        : 'Не указана';
    final showDatePrompt = _isDateSuspicious(_warnings) && !_dateIgnored;

    return Scaffold(
      appBar: AppBar(title: const Text('Подтверждение чека')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          if (_warnings.isNotEmpty) ...[
            Material(
              color: scheme.errorContainer.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Проверьте данные',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: scheme.onErrorContainer,
                          ),
                    ),
                    const SizedBox(height: 6),
                    ..._warnings.map(
                      (w) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text(
                          '• $w',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: scheme.onErrorContainer,
                              ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
          TextField(
            controller: _storeController,
            decoration: const InputDecoration(
              labelText: 'Магазин',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Дата покупки'),
            subtitle: Text(dateLabel),
            trailing: IconButton(
              tooltip: 'Изменить дату',
              onPressed: _pickDate,
              icon: const Icon(Icons.edit_calendar_outlined),
            ),
          ),
          if (showDatePrompt) ...[
            Card(
              elevation: 0,
              color: scheme.secondaryContainer.withValues(alpha: 0.45),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Проверьте дату',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        FilledButton.tonal(
                          onPressed: _pickDate,
                          child: const Text('Изменить'),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton(
                          onPressed: () => setState(() {
                            _dateIgnored = true;
                            _dateConfirmed = false;
                          }),
                          child: const Text('Не важно'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
          TextField(
            controller: _totalController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Итого',
              border: OutlineInputBorder(),
              suffixText: '₽',
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Позиции',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 8),
          ...List.generate(_items.length, (index) {
            final item = _items[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              elevation: 0,
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  children: [
                    TextFormField(
                      initialValue: item.nameDisplay ?? item.name,
                      decoration: const InputDecoration(
                        labelText: 'Название',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      onChanged: (v) {
                        item.nameDisplay = v;
                        item.name = v;
                      },
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            initialValue: item.qty,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: const InputDecoration(
                              labelText: 'Кол-во',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            onChanged: (v) {
                              item.qty = v;
                              item.sum = _recalcSum(item.qty, item.price);
                              setState(() {});
                            },
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextFormField(
                            initialValue: item.price,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: const InputDecoration(
                              labelText: 'Цена',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            onChanged: (v) {
                              item.price = v;
                              item.sum = _recalcSum(item.qty, item.price);
                              setState(() {});
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String?>(
                      key: ValueKey('cat_${index}_${item.categorySlug}'),
                      initialValue: item.categorySlug,
                      decoration: const InputDecoration(
                        labelText: 'Категория',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      items: [
                        const DropdownMenuItem<String?>(
                          value: null,
                          child: Text('—'),
                        ),
                        ..._categoryOptions.map(
                          (c) => DropdownMenuItem<String?>(
                            value: c.slug,
                            child: Text(c.label),
                          ),
                        ),
                      ],
                      onChanged: (v) => setState(() => item.categorySlug = v),
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: Text(
                        'Сумма: ${item.sum}',
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _saving ? null : () => _submit(saveAsDraft: false),
            child: _saving
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Сохранить чек'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _saving ? null : () => _submit(saveAsDraft: true),
            child: const Text('Сохранить и исправить позже'),
          ),
        ],
      ),
    );
  }
}
