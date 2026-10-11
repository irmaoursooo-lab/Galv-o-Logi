import 'dart:convert';
import 'package:http/http.dart' as http;
import 'offline_db_service.dart';

/// Worker assíncrono que envia eventos offline para a nuvem quando há conexão
class OutboxSyncWorker {
  final OfflineDbService _dbService = OfflineDbService();
  final String backendBaseUrl;

  OutboxSyncWorker({this.backendBaseUrl = 'http://localhost:8000'});

  Future<int> synchronize() async {
    final pending = await _dbService.getPendingEvents();
    if (pending.isEmpty) return 0;

    final url = Uri.parse('$backendBaseUrl/api/v1/sync/batch');
    final payload = {
      'driver_id': 'driver_flutter',
      'events': pending.map((e) => e.toJson()).toList(),
    };

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final syncedIds = (data['synced_ids'] as List<dynamic>).map((e) => e.toString()).toList();
        await _dbService.markEventsSynced(syncedIds);
        return syncedIds.length;
      }
    } catch (e) {
      // Dispositivo sem conexão ou servidor offline; continuará enfileirado localmente
    }
    return 0;
  }
}
