function makeRequest(code, text) {
  return {
    'code_b64': btoa(code),
    'kwargs_b64': btoa('{"text": "' + text + '"}')
  };
}

async function getAudio(url, code, text, onChunk, onDone) {
  let response = await fetch(url, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify(makeRequest(code, text))
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const reader = response.body.getReader();
  reader.read().then(({ done, chunk }) => {
    if (chunk) {
      onChunk(chunk);
    }
    if (done) {
      onDone();
    }
  });
}
