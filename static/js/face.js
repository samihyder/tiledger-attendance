/* Face reading for the attendance app — the face is only READ here (face-api,
 * in the browser); matching and saving happen in TiLedger. One reading =
 * the average of 3 frames, as before. */
const Face = (() => {
  const FRAMES = 3, GAP_MS = 400, MIN_CONF = 0.45
  let ready = false, stream = null

  async function load(modelUrl) {
    if (ready) return
    await faceapi.nets.ssdMobilenetv1.loadFromUri(modelUrl)
    await faceapi.nets.faceLandmark68Net.loadFromUri(modelUrl)
    await faceapi.nets.faceRecognitionNet.loadFromUri(modelUrl)
    ready = true
  }

  async function start(video) {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } })
    video.srcObject = stream
    await new Promise(r => { if (video.readyState >= 2) r(); else video.onloadeddata = r })
  }

  async function frame(video) {
    const det = await faceapi.detectSingleFace(video, new faceapi.SsdMobilenetv1Options({ minConfidence: MIN_CONF }))
      .withFaceLandmarks().withFaceDescriptor()
    return det ? { d: Array.from(det.descriptor), score: det.detection.score } : null
  }

  /** Returns { descriptor[128], quality } or null when no face was seen in enough frames. */
  async function read(video, onStep) {
    const got = []
    for (let i = 0; i < FRAMES + 2 && got.length < FRAMES; i++) {
      if (onStep) onStep(got.length, FRAMES)
      const f = await frame(video)
      if (f) got.push(f)
      await new Promise(r => setTimeout(r, GAP_MS))
    }
    if (got.length < 2) return null
    const descriptor = new Array(128).fill(0)
    for (const f of got) f.d.forEach((x, k) => { descriptor[k] += x / got.length })
    return { descriptor, quality: Math.round(got.reduce((t, f) => t + f.score, 0) / got.length * 100) / 100 }
  }

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID()
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3 | 8)).toString(16) })
  }

  async function post(url, body) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), credentials: 'same-origin' })
    const json = await res.json().catch(() => ({ success: false, error: 'Bad reply' }))
    return { status: res.status, ...json }
  }

  return { load, start, read, uuid, post }
})()
