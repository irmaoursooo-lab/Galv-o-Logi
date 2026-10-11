class ItineraryStopModel {
  final int stepNumber;
  final String stopType;
  final String? destinationId;
  final String name;
  final String address;
  final double latitude;
  final double longitude;
  final String arrivalTime;
  final String departureTime;
  final int serviceDurationMinutes;
  final double distanceFromPreviousKm;
  final int travelTimeFromPreviousMinutes;
  final bool isSlowDock;
  final String? slowDockWarning;
  final String? mealType;
  final String? notes;

  ItineraryStopModel({
    required this.stepNumber,
    required this.stopType,
    this.destinationId,
    required this.name,
    required this.address,
    required this.latitude,
    required this.longitude,
    required this.arrivalTime,
    required this.departureTime,
    required this.serviceDurationMinutes,
    required this.distanceFromPreviousKm,
    required this.travelTimeFromPreviousMinutes,
    this.isSlowDock = false,
    this.slowDockWarning,
    this.mealType,
    this.notes,
  });

  factory ItineraryStopModel.fromJson(Map<String, dynamic> json) {
    return ItineraryStopModel(
      stepNumber: json['step_number'] ?? 1,
      stopType: json['stop_type'] ?? 'DELIVERY',
      destinationId: json['destination_id'],
      name: json['name'] ?? '',
      address: json['address'] ?? '',
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      arrivalTime: json['arrival_time'] ?? '',
      departureTime: json['departure_time'] ?? '',
      serviceDurationMinutes: json['service_duration_minutes'] ?? 0,
      distanceFromPreviousKm: (json['distance_from_previous_km'] as num?)?.toDouble() ?? 0.0,
      travelTimeFromPreviousMinutes: json['travel_time_from_previous_minutes'] ?? 0,
      isSlowDock: json['is_slow_dock'] ?? false,
      slowDockWarning: json['slow_dock_warning'],
      mealType: json['meal_type'],
      notes: json['notes'],
    );
  }
}

class RouteResponseModel {
  final String routeId;
  final int totalStops;
  final double totalDistanceKm;
  final int totalDurationMinutes;
  final String estimatedEndTime;
  final List<ItineraryStopModel> itinerary;
  final String ttsBriefing;
  final int antiIdleSavedMinutes;
  final int chronicDocksPrioritized;
  final List<List<double>>? roadGeometry;

  RouteResponseModel({
    required this.routeId,
    required this.totalStops,
    required this.totalDistanceKm,
    required this.totalDurationMinutes,
    required this.estimatedEndTime,
    required this.itinerary,
    required this.ttsBriefing,
    required this.antiIdleSavedMinutes,
    required this.chronicDocksPrioritized,
    this.roadGeometry,
  });

  factory RouteResponseModel.fromJson(Map<String, dynamic> json) {
    var rawStops = json['itinerary'] as List<dynamic>? ?? [];
    var stops = rawStops.map((s) => ItineraryStopModel.fromJson(s as Map<String, dynamic>)).toList();
    List<List<double>>? roadGeom;
    if (json['road_geometry'] != null) {
      roadGeom = (json['road_geometry'] as List<dynamic>)
          .map((pt) => (pt as List<dynamic>).map((c) => (c as num).toDouble()).toList())
          .toList();
    }

    return RouteResponseModel(
      routeId: json['route_id'] ?? '',
      totalStops: json['total_stops'] ?? stops.length,
      totalDistanceKm: (json['total_distance_km'] as num?)?.toDouble() ?? 0.0,
      totalDurationMinutes: json['total_duration_minutes'] ?? 0,
      estimatedEndTime: json['estimated_end_time'] ?? '',
      itinerary: stops,
      ttsBriefing: json['tts_briefing'] ?? '',
      antiIdleSavedMinutes: json['anti_idle_saved_minutes'] ?? 0,
      chronicDocksPrioritized: json['chronic_docks_prioritized'] ?? 0,
      roadGeometry: roadGeom,
    );
  }
}
