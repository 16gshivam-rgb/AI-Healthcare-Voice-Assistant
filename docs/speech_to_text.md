# Speech-to-text configuration and IndicConformer assessment

## User flow and data handling

CareVoice keeps browser speech recognition as the default. Choose one backend provider with `SPEECH_TO_TEXT_PROVIDER`:

| Value | Behavior |
| --- | --- |
| `browser` | Uses the browser's `SpeechRecognition` implementation. Browser support and audio processing are controlled by that browser/vendor; typed input remains available. |
| `openai_compatible` | Uploads audio to `{SPEECH_TO_TEXT_BASE_URL}/audio/transcriptions`, or to the configured LLM base URL when an LLM API key is set. Sends `file`, `language`, `model`, and `response_format=json` multipart fields. |
| `indicconformer` | Uploads audio to the exact `SPEECH_TO_TEXT_BASE_URL`. This must be an operator-hosted adapter implementing the same multipart fields and returning `{"text":"..."}`. It is not downloaded or run by this application. |

The backend accepts `hi` and `en`, caps each uploaded recording at `SPEECH_TO_TEXT_MAX_AUDIO_BYTES` (10 MiB by default), applies a bounded provider timeout, and does not persist the audio or transcript. Audio is sent only when the user explicitly starts recording and then stops it. The UI shows the transcript in an editable field and requires confirmation before it can be submitted to chat. Typed entry is always available. The chat request—including a confirmed transcript—runs deterministic emergency and safety checks before any RAG retrieval or LLM call.

For a hosted provider, configure its URL and credential in backend environment variables. Do not put speech credentials in frontend build variables. Hosted audio and text leave the local environment; review provider privacy, retention, and regional processing terms before use.

## AI4Bharat IndicConformer Hindi assessment

The [AI4Bharat IndicConformerASR repository](https://github.com/AI4Bharat/IndicConformerASR) describes an Indic-language ASR suite and lists Hindi among its monolingual models. Its repository license is MIT ([LICENSE](https://github.com/AI4Bharat/IndicConformerASR/blob/master/LICENSE)). The [Hindi Hugging Face model card](https://huggingface.co/ai4bharat/indicconformer_stt_hi_hybrid_ctc_rnnt_large) describes a 120-million-parameter Conformer-Large with a hybrid CTC/RNNT decoder. Its documented input is 16 kHz, mono-channel WAV; its usage instructions rely on AI4Bharat's NeMo fork and PyTorch.

**Assessment:** IndicConformer is a relevant Hindi ASR candidate and may be deployed behind the adapter contract above. It is not included in the default Compose stack: the model/runtime have significant deployment dependencies and hardware/latency requirements that must be sized on the target host. The model card's repository license does not by itself establish the exact terms for every downloaded checkpoint or associated dataset; verify the selected artifact and data terms before deployment. The application does not silently choose IndicConformer or send audio to it.

No representative Hindi/Hinglish patient-speech corpus, microphone test set, or target-hardware benchmark was available for this change. Therefore no word-error rate, latency comparison, dialect/noise result, or accuracy claim is reported. Before use beyond development, evaluate with consented or properly licensed and de-identified speech spanning Hindi scripts, Hinglish/code-switching, accents, background noise, and clinically important symptom terms. Have reviewers measure word error rate and critical symptom-term error rates. ASR output is not medically validated; users must confirm it, and clinicians must not rely on it as a complete or exact history.

## Adapter contract for an IndicConformer deployment

The configured adapter accepts:

```text
POST /transcribe
Content-Type: multipart/form-data
file=<audio bytes>
language=hi
model=<configured model identifier>
response_format=json
```

It returns JSON with a non-empty string field named `text`. The adapter is responsible for safely decoding browser audio containers and preparing 16 kHz mono WAV input for the documented Hindi model. Keep it on a trusted private network, authenticate it where supported, enforce its own upload and resource limits, and do not log audio or transcript content. On any adapter failure CareVoice reports an error and keeps the typed-input path; it does not fall back to another speech or language model.
