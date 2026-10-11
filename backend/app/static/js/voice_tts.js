/**
 * GALVÃO LOGI — COPILOTO DE VOZ SINTÉTICA (TEXT-TO-SPEECH)
 * Executa avisos de áudio de 1 frase ultracurta e direta em português brasileiro.
 */

class VoiceCopilot {
  constructor() {
    this.synth = window.speechSynthesis;
    this.voice = null;
    this.isMuted = localStorage.getItem('galvao_voice_muted') === 'true';
    this.initVoice();
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    localStorage.setItem('galvao_voice_muted', this.isMuted);
    if (this.isMuted && this.synth) {
      this.synth.cancel();
    }
    return this.isMuted;
  }

  initVoice() {
    if (!this.synth) return;
    const load = () => {
      const voices = this.synth.getVoices();
      // Priorizar voz natural em pt-BR
      this.voice = voices.find(v => v.lang === 'pt-BR') || voices.find(v => v.lang.startsWith('pt')) || null;
    };
    load();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = load;
    }
  }

  speak(text) {
    if (this.isMuted || !this.synth || !text) return;
    this.synth.cancel(); // Cancela áudios anteriores para não sobrepor

    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'pt-BR';
    utter.rate = 1.05; // Levemente ágil para comandos de direção
    utter.pitch = 1.0;
    if (this.voice) {
      utter.voice = this.voice;
    }

    this.synth.speak(utter);
  }

  vibrate(duration = 40) {
    if ('vibrate' in navigator) {
      navigator.vibrate(duration);
    }
  }
}

window.voiceCopilot = new VoiceCopilot();
