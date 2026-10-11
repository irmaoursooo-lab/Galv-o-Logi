import os
from typing import Dict, Any, List, Optional

class SyntheticVoiceCopilotAgent:
    """
    Agente 6: Copiloto de Voz Sintética & Mensagens Ultracurtas (Gemini AI)
    Garante mensagens ultracurtas (zero textões) para condução segura.
    Gera instruções de áudio TTS de 1 frase objetiva em português brasileiro.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def generate_driving_audio_cue(
        self,
        event_type: str,
        saved_minutes: Optional[int] = None,
        destination_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Retorna o texto visual resumido para a tela (HUD) e a frase de áudio para o TTS.
        """
        if event_type == "REROUTE_SAVINGS":
            mins = saved_minutes or 5
            return {
                "hud_title": f"⚡ ECONOMIZA {mins} MIN",
                "hud_subtitle": "Trânsito Lento à Frente",
                "hud_action_primary": "ACEITAR",
                "hud_action_secondary": "MANTER",
                "tts_speech": f"Nova rota economiza {mins} minutos. Toque em aceitar ou vire à direita."
            }

        elif event_type == "SLOW_DOCK_PRIORITIZED":
            name = destination_name or "Próxima parada"
            return {
                "hud_title": "DOCA ADIANTADA",
                "hud_subtitle": f"{name} (Evita fila)",
                "hud_action_primary": "VER ROTA",
                "hud_action_secondary": "OK",
                "tts_speech": f"Parada adiantada para início da manhã, evitando fila de espera na doca."
            }

        elif event_type == "MEAL_RECOMMENDATION":
            return {
                "hud_title": "HORA DO ALMOÇO",
                "hud_subtitle": "Restaurante a 800m (Nota 4.7)",
                "hud_action_primary": "PARAR AQUI",
                "hud_action_secondary": "SEGUIR",
                "tts_speech": "Restaurante Fogão Gaúcho a oitocentos metros da rota. Toque para almoçar aqui."
            }

        elif event_type == "HEIGHT_RESTRICTION":
            return {
                "hud_title": "⛔ VIADUTO BAIXO",
                "hud_subtitle": "Desvio Ativado",
                "hud_action_primary": "SEGUIR DESVIO",
                "hud_action_secondary": "DETALHES",
                "tts_speech": "Atenção: viaduto baixo à frente. Rota ajustada para altura do seu caminhão."
            }

        elif event_type == "WEIGHT_RESTRICTION":
            return {
                "hud_title": "⛔ LIMITE DE PESO",
                "hud_subtitle": "Desvio Ativado",
                "hud_action_primary": "SEGUIR DESVIO",
                "hud_action_secondary": "DETALHES",
                "tts_speech": "Atenção: limite de peso na via. Rota ajustada para o peso do seu caminhão."
            }

        else:
            return {
                "hud_title": "EM NAVEGAÇÃO",
                "hud_subtitle": "Siga pela rota destacada",
                "hud_action_primary": "OK",
                "hud_action_secondary": "",
                "tts_speech": "Siga na rota principal."
            }

    def generate_planning_briefing(self, stops_count: int, total_time_min: int, slow_docks_count: int) -> str:
        """
        Resumo limpo estilo Apple para o motorista antes de dar partida.
        """
        hours = total_time_min // 60
        mins = total_time_min % 60
        time_str = f"{hours}h {mins}min" if hours > 0 else f"{mins} min"

        points = [
            f"• Itinerário com {stops_count} paradas ({time_str} estimado).",
        ]
        if slow_docks_count > 0:
            points.append(f"• {slow_docks_count} doca(s) com histórico de lentidão reordenada(s) para fluidez.")
        points.append("• Parada de almoço programada em restaurante com estacionamento.")

        return "\n".join(points)
