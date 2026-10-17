// Bounded, nonsecret device-derived presentation; never an authentication proof.
export async function titleFromDevice(suffix, expectedDevice) {
  try {
    const response = await fetch('/api/presentation/v1', {cache:'no-store',credentials:'omit',
      redirect:'error',signal:AbortSignal.timeout(2000)});
    if (!response.ok) return;
    const data = await response.json();
    if (data.schema !== 'device-presentation/1' || data.device_id !== expectedDevice ||
        !/^[0-9a-f]{32}$/.test(data.boot_id) || typeof data.hostname !== 'string' ||
        !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local$/.test(data.hostname)) return;
    document.title = data.hostname + ' - ' + suffix;
    return data.hostname;
  } catch { /* Preserve the honest generic title when metadata is unavailable. */ }
}
