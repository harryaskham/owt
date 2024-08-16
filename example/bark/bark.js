function makeRequest(code, text, speaker) {
  return {
    'code_b64': btoa(code),
    'kwargs_b64': btoa(JSON.stringify({
      'text': text,
      'speaker': speaker
    })),
  };
}

function audioUrl(url, code, text, speaker) {
  const request = makeRequest(code, text, speaker);
  return url + '?' + $.param(request);
}

async function getAudio(url, code, text, speaker, onChunk) {
  const source = new EventSource(audioUrl(url, code, text, speaker));
  source.onmessage = function(event) {
    if (event.data.toLowerCase() == 'done') {
      source.close();
      return;
    }
    const chunk = JSON.parse(event.data);
    onChunk(chunk);
  }
}
