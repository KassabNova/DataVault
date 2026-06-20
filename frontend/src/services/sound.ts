const ctx = () => new (window.AudioContext || (window as any).webkitAudioContext)()

export function playSuccess() {
  try {
    const a = ctx(); const o = a.createOscillator(); const g = a.createGain()
    o.connect(g); g.connect(a.destination)
    o.frequency.value = 880; g.gain.value = 0.3
    o.start(); o.stop(a.currentTime + 0.1)
  } catch {}
}

export function playScanMatch() {
  try {
    const a = ctx(); const o = a.createOscillator(); const g = a.createGain()
    o.connect(g); g.connect(a.destination)
    o.frequency.setValueAtTime(660, a.currentTime)
    o.frequency.setValueAtTime(880, a.currentTime + 0.08)
    g.gain.value = 0.2
    o.start(); o.stop(a.currentTime + 0.15)
  } catch {}
}
