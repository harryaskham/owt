function makeRequest(code, text) {
  return {
    'code_b64': btoa(code),
    'kwargs_b64': btoa('{"text": "' + text + '"}')
  };
}

async function getAudio(url, code, text, onChunk, onDone) {
  const response = await fetch(url, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify(makeRequest(code, text))
  });
  const reader = response.body.getReader();
  let result = await reader.read();
  while (!result.done) {
    const chunk = result.value;
    console.log("result is", result)
    console.log("chunk is", chunk)
    onChunk(chunk)
    result = await reader.read()
  }
  onDone();
}
