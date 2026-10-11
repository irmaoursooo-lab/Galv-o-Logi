class OfflineEventModel {
  final String id;
  final String eventType;
  final Map<String, dynamic> payload;
  final String createdAtLocal;
  String syncStatus;

  OfflineEventModel({
    required this.id,
    required this.eventType,
    required this.payload,
    required this.createdAtLocal,
    this.syncStatus = 'PENDING',
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'event_type': eventType,
    'payload': payload,
    'created_at_local': createdAtLocal,
    'sync_status': syncStatus,
  };

  factory OfflineEventModel.fromJson(Map<String, dynamic> json) => OfflineEventModel(
    id: json['id'],
    eventType: json['event_type'],
    payload: json['payload'] as Map<String, dynamic>,
    createdAtLocal: json['created_at_local'],
    syncStatus: json['sync_status'] ?? 'PENDING',
  );
}
