function makeRequest(code, text, speaker, sentenceTemplate, splitType) {
  return {
    'code_b64': btoa(code),
    'kwargs_b64': btoa(JSON.stringify({
      'text': text.replace(/\n/g, '\\n'),
      'speaker': speaker,
      'sentence_template': sentenceTemplate,
      'split_type': splitType
    })),
  };
}

function audioUrl(
  url, code, text, speaker, sentenceTemplate, splitType) {
  const request = makeRequest(
    code, text, speaker, sentenceTemplate, splitType);
  return url + '?' + $.param(request);
}

async function getAudio(
  url, code, text, speaker, sentenceTemplate, splitType, onChunk) {
  const source = new EventSource(
    audioUrl(url, code, text, speaker, sentenceTemplate, splitType));
  source.onmessage = function(event) {
    if (event.data.toLowerCase() == 'done') {
      source.close();
      return;
    }
    const chunk = JSON.parse(event.data);
    onChunk(chunk);
  }
}
