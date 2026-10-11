import 'package:flutter/services.dart';

/// Serviço de voz e vibração tátil para instruções de condução
class TtsVoiceService {
  static bool isMuted = false;

  static bool toggleMute() {
    isMuted = !isMuted;
    return isMuted;
  }

  static Future<void> speak(String text) async {
    if (isMuted || text.isEmpty) return;
    // Comunicação com sintetizador nativo via platform channels ou flutter_tts
    // Mantém mensagens ultracurtas (zero distração)
  }

  static void hapticFeedback() {
    HapticFeedback.mediumImpact();
  }
}
