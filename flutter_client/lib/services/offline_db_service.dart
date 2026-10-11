import 'dart:convert';
import '../models/offline_event.dart';

/// Serviço local que gerencia a tabela `offline_events_queue`
/// (Simulação com persistência em cache local e Drift/SQLite)
class OfflineDbService {
  static final OfflineDbService _instance = OfflineDbService._internal();
  factory OfflineDbService() => _instance;
  OfflineDbService._internal();

  final List<OfflineEventModel> _queue = [];

  Future<void> enqueueEvent(String eventType, Map<String, dynamic> payload) async {
    final event = OfflineEventModel(
      id: 'evt_${DateTime.now().millisecondsSinceEpoch}',
      eventType: eventType,
      payload: payload,
      createdAtLocal: DateTime.now().toIso8601String(),
      syncStatus: 'PENDING',
    );
    _queue.add(event);
  }

  Future<List<OfflineEventModel>> getPendingEvents() async {
    return _queue.where((e) => e.syncStatus == 'PENDING').toList();
  }

  Future<void> markEventsSynced(List<String> eventIds) async {
    final set = eventIds.toSet();
    for (var event in _queue) {
      if (set.contains(event.id)) {
        event.syncStatus = 'SYNCED';
      }
    }
    _queue.removeWhere((e) => e.syncStatus == 'SYNCED');
  }

  int get pendingCount => _queue.where((e) => e.syncStatus == 'PENDING').length;
}
