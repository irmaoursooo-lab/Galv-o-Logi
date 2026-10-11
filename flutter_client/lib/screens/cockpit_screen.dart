import 'package:flutter/material.dart';
import '../theme/apple_cupertino_theme.dart';
import '../services/tts_voice_service.dart';
import '../services/offline_db_service.dart';
import 'slow_dock_dialog.dart';

/// Cockpit de Direção Oficial (Ergonomia Apple para Baixa Instrução e Zero Distração)
class CockpitScreen extends StatefulWidget {
  const CockpitScreen({Key? key}) : super(key: key);

  @override
  State<CockpitScreen> createState() => _CockpitScreenState();
}

class _CockpitScreenState extends State<CockpitScreen> {
  bool _showRerouteAlert = false;
  int _savedMinutes = 8;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppleTokens.deepSpaceBlack,
      body: Stack(
        children: [
          // 1. Fundo do Mapa de Navegação
          Container(
            color: const Color(0xFF121214),
            child: const Center(
              child: Text(
                '🗺️ [Mapa Vetorial Minimalista Dark Mode]',
                style: TextStyle(color: AppleTokens.textSecondaryDark, fontSize: 16),
              ),
            ),
          ),

          // 2. Barra Superior: Top Island Apple HUD
          Positioned(
            top: 48,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                AppleTokens.frostedGlassContainer(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  child: Row(
                    children: [
                      Container(
                        width: 14,
                        height: 14,
                        decoration: const BoxDecoration(
                          color: AppleTokens.systemGreen,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 14),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            '1. Mercado Central Doca Sul',
                            style: TextStyle(
                              color: AppleTokens.textPrimaryDark,
                              fontWeight: FontWeight.bold,
                              fontSize: 18,
                            ),
                          ),
                          Text(
                            'Av. das Amoras, 420 • Doca 14 (Priorizada)',
                            style: TextStyle(
                              color: AppleTokens.textSecondaryDark,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(width: 24),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: const [
                          Text(
                            '08:15',
                            style: TextStyle(
                              color: AppleTokens.systemGreen,
                              fontWeight: FontWeight.w800,
                              fontSize: 22,
                            ),
                          ),
                          Text(
                            'CHEGADA',
                            style: TextStyle(
                              color: AppleTokens.textSecondaryDark,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                Row(
                  children: [
                    // Botão de Mutar / Desmutar Guia de Voz
                    IconButton(
                      icon: Icon(
                        TtsVoiceService.isMuted ? Icons.volume_off : Icons.volume_up,
                        color: TtsVoiceService.isMuted ? AppleTokens.coralRed : AppleTokens.textPrimaryDark,
                      ),
                      tooltip: TtsVoiceService.isMuted ? 'Desmutar Guia' : 'Silenciar Guia',
                      onPressed: () {
                        TtsVoiceService.hapticFeedback();
                        setState(() {
                          TtsVoiceService.toggleMute();
                        });
                      },
                    ),
                    const SizedBox(width: 8),
                    // Pílula de Conexão Offline / Online
                    AppleTokens.frostedGlassContainer(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      child: Row(
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: AppleTokens.systemGreen,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            'Online (Outbox: 0)',
                            style: TextStyle(color: AppleTokens.textPrimaryDark, fontSize: 12, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // 3. Alerta Flutuante de Reroteamento (Gatilho >= 4 minutos)
          if (_showRerouteAlert)
            Positioned(
              bottom: 120,
              left: 30,
              right: 30,
              child: AppleTokens.frostedGlassContainer(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          '🚗🚗 Trânsito Lento à Frente',
                          style: TextStyle(color: AppleTokens.textSecondaryDark, fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '⚡ -$_savedMinutes MIN',
                          style: const TextStyle(
                            color: AppleTokens.systemGreen,
                            fontSize: 32,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppleTokens.systemGreen,
                              foregroundColor: Colors.black,
                              minimumSize: const Size(0, 64),
                              shape: RoundedRectangleBorder(borderRadius: AppleTokens.capsuleRadius),
                            ),
                            onPressed: () {
                              TtsVoiceService.hapticFeedback();
                              setState(() => _showRerouteAlert = false);
                            },
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: const [
                                Text('🟢 ACEITAR', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                                Text('(Toque ou vire à direita)', style: TextStyle(fontSize: 11)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.white.withOpacity(0.12),
                              foregroundColor: AppleTokens.textPrimaryDark,
                              minimumSize: const Size(0, 64),
                              shape: RoundedRectangleBorder(borderRadius: AppleTokens.capsuleRadius),
                            ),
                            onPressed: () {
                              TtsVoiceService.hapticFeedback();
                              setState(() => _showRerouteAlert = false);
                            },
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: const [
                                Text('⚪ MANTER', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                                Text('(Rota Atual)', style: TextStyle(fontSize: 11)),
                              ],
                            ),
                          ),
                        ),
                      ],
                    )
                  ],
                ),
              ),
            ),

          // 4. Barra Inferior do Cockpit
          Positioned(
            bottom: 24,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                AppleTokens.frostedGlassContainer(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                  child: Row(
                    children: const [
                      Text('4 Paradas  •  48.2 km  •  Término 14:20',
                        style: TextStyle(color: AppleTokens.textPrimaryDark, fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppleTokens.amberCaution.withOpacity(0.20),
                    foregroundColor: AppleTokens.amberCaution,
                    side: const BorderSide(color: AppleTokens.amberCaution, width: 0.5),
                    minimumSize: const Size(200, 60),
                    shape: RoundedRectangleBorder(borderRadius: AppleTokens.capsuleRadius),
                  ),
                  onPressed: () {
                    TtsVoiceService.hapticFeedback();
                    showDialog(
                      context: context,
                      builder: (ctx) => const SlowDockDialog(destinationName: 'Mercado Central Doca Sul'),
                    );
                  },
                  icon: const Icon(Icons.access_time_filled),
                  label: const Text('Reportar Doca Lenta', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }
}
