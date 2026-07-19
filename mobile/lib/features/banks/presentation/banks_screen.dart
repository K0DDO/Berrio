import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/widgets/journey_state_panel.dart';
import '../data/banks_api.dart';

const _banks = <({String code, String label, String instruction})>[
  (
    code: 'sber',
    label: 'Сбер',
    instruction:
        'В приложении Сбер → История → Выписка → скачайте PDF или CSV и загрузите сюда.',
  ),
  (
    code: 'tbank',
    label: 'Т-Банк',
    instruction:
        'Лучше CSV: на компьютере tbank.ru → Операции → период → Поделиться → CSV. '
        'PDF часто без текста и не разбирается.',
  ),
  (
    code: 'alfa',
    label: 'Альфа',
    instruction:
        'Альфа-Онлайн → Выписки → скачайте файл (PDF/CSV/XLSX) и прикрепите.',
  ),
  (
    code: 'vtb',
    label: 'ВТБ',
    instruction:
        'ВТБ Онлайн → Выписки и справки → скачайте выписку и загрузите сюда.',
  ),
  (
    code: 'other',
    label: 'Другой банк',
    instruction:
        'Экспортируйте выписку в PDF, CSV или XLSX и загрузите файл для сверки.',
  ),
];

class BanksScreen extends ConsumerStatefulWidget {
  const BanksScreen({super.key});

  @override
  ConsumerState<BanksScreen> createState() => _BanksScreenState();
}

class _BanksScreenState extends ConsumerState<BanksScreen> {
  String _bankCode = 'sber';
  var _uploading = false;
  List<String> _messages = const [];
  String? _error;

  ({String code, String label, String instruction}) get _selected =>
      _banks.firstWhere((b) => b.code == _bankCode);

  String _friendlyError(Object error) {
    if (error is DioException) {
      final code = error.response?.statusCode;
      if (code == 404) {
        return 'Сервер ещё без загрузки выписок. Обновите приложение после деплоя API или попробуйте позже.';
      }
      if (code == 401 || code == 403) {
        return 'Нужно войти в аккаунт заново.';
      }
      if (code == 413) {
        return 'Файл слишком большой (макс. 15 МБ).';
      }
      if (code == 422) {
        final detail = error.response?.data;
        if (detail is Map && detail['detail'] != null) {
          return detail['detail'].toString();
        }
        return 'Не удалось разобрать выписку. Попробуйте CSV или XLSX.';
      }
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout) {
        return 'Нет связи с сервером. Проверьте интернет.';
      }
    }
    return 'Не удалось загрузить выписку. Попробуйте другой формат файла.';
  }

  Future<void> _pickAndUpload() async {
    setState(() {
      _error = null;
      _messages = const [];
    });
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'csv', 'xlsx', 'xls'],
      withData: false,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.single;
    final path = file.path;
    if (path == null) {
      setState(() => _error = 'Не удалось прочитать файл');
      return;
    }

    setState(() => _uploading = true);
    try {
      final out = await ref.read(banksApiProvider).uploadStatement(
            bankCode: _bankCode,
            filePath: path,
            fileName: file.name,
          );
      if (!mounted) return;
      setState(() => _messages = out.messages);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = _friendlyError(e));
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Банковские выписки')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Text(
            'Выберите банк',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _banks.map((b) {
              return ChoiceChip(
                label: Text(b.label),
                selected: _bankCode == b.code,
                onSelected: (_) => setState(() => _bankCode = b.code),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(_selected.instruction),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _uploading ? null : _pickAndUpload,
            icon: _uploading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.upload_file),
            label: Text(_uploading ? 'Загрузка…' : 'Выбрать файл (PDF/CSV/XLSX)'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            JourneyStatePanel.error(
              message: _error!,
              onRetry: _pickAndUpload,
            ),
          ],
          if (_messages.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Сверка',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 8),
            ..._messages.map(
              (m) => Card(
                child: ListTile(
                  leading: const Icon(Icons.check_circle_outline),
                  title: Text(m),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
