from owt.lib import bark
from unittest import mock
import numpy as np

@mock.patch("bark.generation.preload_models")
@mock.patch("bark.generation.generate_text_semantic")
@mock.patch("bark.api.semantic_to_waveform")
@mock.patch("base64.b64encode")
@mock.patch("scipy.io.wavfile.write")
@mock.patch("nltk.sent_tokenize")
def test_bark(
    mock_sent_tokenize,
    mock_wavwrite,
    mock_b64encode,
    mock_semantic_to_waveform,
    mock_generate_text_semantic,
    mock_preload_models,
):
    mock_sent_tokenize.side_effect = lambda x: x.split(".")
    mock_b64encode.side_effect = lambda x: x
    mock_wavwrite.side_effect = lambda buf, _, arr: buf.write(arr)
    mock_wav_1 = mock.MagicMock()
    mock_wav_2 = mock.MagicMock()
    mock_tokens = {
        "Sentence 1": mock_wav_1,
        "Sentence 2": mock_wav_2,
    }
    mock_wavs = {
        mock_wav_1: np.array(list(map(ord, "wav1")), dtype=np.byte),
        mock_wav_2: np.array(list(map(ord, "wav2")), dtype=np.byte),
    }
    mock_preload_models.return_value = None
    mock_generate_text_semantic.side_effect = lambda sentence, **kwargs: mock_tokens[
        sentence
    ]
    mock_semantic_to_waveform.side_effect = lambda tokens, **_: mock_wavs[tokens]
    data, extra_headers = bark.run(text="Sentence 1.Sentence 2")

    stream = list(data)
    assert stream == [
        'data: {"chunk": "wav1", "cumulative": "wav1"}\n\n',
        'data: {"chunk": "wav2", "cumulative": "wav1wav2"}\n\n',
        "data: [DONE]\n\n",
    ]
    assert extra_headers == {"Content-Type": "text/event-stream"}
    mock_preload_models.assert_called_once()
    mock_generate_text_semantic.assert_has_calls(
        [
            mock.call(
                "Sentence 1",
                history_prompt=mock.ANY,
                temp=mock.ANY,
                min_eos_p=mock.ANY,
            ),
            mock.call(
                "Sentence 2",
                history_prompt=mock.ANY,
                temp=mock.ANY,
                min_eos_p=mock.ANY,
            ),
        ]
    )
    mock_semantic_to_waveform.assert_has_calls(
        [
            mock.call(mock_tokens["Sentence 1"], history_prompt=mock.ANY),
            mock.call(mock_tokens["Sentence 2"], history_prompt=mock.ANY),
        ]
    )
