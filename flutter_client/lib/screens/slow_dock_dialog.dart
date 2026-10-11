import 'package:flutter/material.dart';
import '../theme/apple_cupertino_theme.dart';
import '../services/tts_voice_service.dart';
import '../services/offline_db_service.dart';

/// Diálogo de 2 Toques para Apontamento de Recebimento Lento
class SlowDockDialog extends StatefulWidget {
  final String destinationName;

  const SlowDockDialog({Key? key, required this.destinationName}) : super(key: key);

  @override
  State<SlowDockDialog> createState() => _SlowDockDialogState();
}

class _SlowDockDialogState extends State<SlowDockDialog> {
  int _selectedMinutes = 60;

  final List<int> _options = [30, 60, 90, 120, 180, 240];

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: AppleTokens.frostedGlassContainer(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.timer_outlined, color: AppleTokens.amberCaution, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Recebimento Lento',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: AppleTokens.textPrimaryDark,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Toque no tempo de espera excedente em: ${widget.destinationName}',
              style: const TextStyle(fontSize: 13, color: AppleTokens.textSecondaryDark),
            ),
            const SizedBox(height: 20),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 2.0,
              children: _options.map((mins) {
                final isSelected = mins == _selectedMinutes;
                return GestureDetector(
                  onTap: () {
                    TtsVoiceService.hapticFeedback();
                    setState(() => _selectedMinutes = mins);
                  },
                  child: Container(
                    decoration: BoxDecoration(
                      color: isSelected ? AppleTokens.amberCaution : Colors.white.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isSelected ? AppleTokens.amberCaution : AppleTokens.hairlineBorderDark,
                        width: 0.5,
                      ),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      mins >= 60 ? '+${mins ~/ 60}h' : '+$mins min',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: isSelected ? Colors.black : AppleTokens.textPrimaryDark,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancelar', style: TextStyle(color: AppleTokens.textSecondaryDark)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppleTokens.systemGreen,
                      foregroundColor: Colors.black,
                      minimumSize: const Size(0, 56),
                      shape: RoundedRectangleBorder(borderRadius: AppleTokens.capsuleRadius),
                    ),
                    onPressed: () async {
                      TtsVoiceService.hapticFeedback();
                      await OfflineDbService().enqueueEvent('SLOW_RECEIVING_REPORT', {
                        'destination_id': widget.destinationName,
                        'excess_wait_minutes': _selectedMinutes,
                        'time_of_day': '${DateTime.now().hour.toString().padLeft(2, '0')}:${DateTime.now().minute.toString().padLeft(2, '0')}',
                      });
                      Navigator.pop(context);
                    },
                    child: const Text('Confirmar (Toque 2)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}
