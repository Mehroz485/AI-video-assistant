import whisper
import os

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # bump up if doing Urdu — small/base struggle on Urdu

LANG_CODES = {"english": "en", "urdu": "ur"}

_whisper_model = None


def load_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        print("Whisper model loaded.")
    return _whisper_model


def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    model = load_whisper_model()
    lang_code = LANG_CODES.get(language.lower())
    result = model.transcribe(chunk_path, task="transcribe", language=lang_code)
    return result["text"]


def transcribe_all(chunks: list, language: str = "english") -> str:
    full_transcript = ""
    print(f"Using Whisper ({WHISPER_MODEL}) for transcription.")

    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")
        full_transcript += transcribe_chunk(chunk, language=language) + " "

    print("Transcription complete.")
    return full_transcript.strip()