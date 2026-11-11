// Original synthesised audio. No microphone or external audio service is used.
export class FieldAudio {
  constructor() { this.enabled = true; this.raining = true; }
  async start() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      this.master = this.ctx.createGain(); this.master.gain.value = this.enabled ? 0.6 : 0; this.master.connect(this.ctx.destination);
      const length = this.ctx.sampleRate * 3;
      this.noise = this.ctx.createBuffer(1, length, this.ctx.sampleRate);
      const data = this.noise.getChannelData(0);
      for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
      const rain = this.ctx.createBufferSource(); rain.buffer = this.noise; rain.loop = true;
      const filter = this.ctx.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 3800;
      this.rainGain = this.ctx.createGain(); this.rainGain.gain.value = this.raining ? 0.065 : 0.012;
      rain.connect(filter); filter.connect(this.rainGain); this.rainGain.connect(this.master); rain.start();
    }
    await this.ctx.resume();
  }
  setEnabled(enabled) { this.enabled = enabled; if(this.master)this.master.gain.setTargetAtTime(enabled ? 0.6 : 0, this.ctx.currentTime, .12); }
  setRain(enabled) { this.raining = enabled; if(this.rainGain)this.rainGain.gain.setTargetAtTime(enabled ? .065 : .012, this.ctx.currentTime, .3); }
  pause() { if(this.ctx?.state === 'running')this.ctx.suspend(); }
  burst(duration, volume, frequency, delay = 0, type = 'lowpass') {
    if(!this.ctx || this.ctx.state !== 'running')return;
    const now=this.ctx.currentTime+delay,source=this.ctx.createBufferSource();source.buffer=this.noise;
    const filter=this.ctx.createBiquadFilter();filter.type=type;filter.frequency.value=frequency;
    const gain=this.ctx.createGain();gain.gain.setValueAtTime(volume,now);gain.gain.exponentialRampToValueAtTime(.001,now+duration);
    source.connect(filter);filter.connect(gain);gain.connect(this.master);source.start(now,Math.random());source.stop(now+duration);
  }
  tone(frequency,duration,volume,type='sine',delay=0,endFrequency=frequency){
    if(!this.ctx||this.ctx.state!=='running')return;
    const now=this.ctx.currentTime+delay,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.type=type;o.frequency.setValueAtTime(frequency,now);o.frequency.exponentialRampToValueAtTime(Math.max(10,endFrequency),now+duration);g.gain.setValueAtTime(volume,now);g.gain.exponentialRampToValueAtTime(.001,now+duration);o.connect(g);g.connect(this.master);o.start(now);o.stop(now+duration);
  }
  fire(){this.burst(.11,.7,6500);this.burst(.2,.29,430);this.tone(160,.12,.43,'triangle',0,38);this.burst(.3,.11,1000,.07);this.burst(.42,.045,700,.18);}
  impact(surface){if(surface==='water'){this.burst(.19,.19,1500);this.burst(.32,.09,420,.025);this.tone(280,.12,.06,'sine',.01,65);return;}if(surface==='metal'){this.tone(1750,.24,.10,'sine');this.tone(3100,.14,.03,'sine',.008);this.burst(.025,.08,4500);}else if(surface==='stone'){this.burst(.06,.15,2400);}else{this.burst(.09,.12,1000);}}
  step(sprint){this.burst(.12,sprint?.105:.075,540);this.burst(.06,.027,4300,.03,'highpass');}
  magazine(){this.burst(.1,.13,1200);this.tone(390,.06,.055,'triangle');}
  bolt(){this.burst(.07,.16,5000);this.burst(.04,.12,2500,.1);}
  empty(){this.tone(350,.045,.07,'square');}
  casing(){this.tone(3200,.08,.018,'sine');}
}
