"""Yüklenen dosya doğrulaması: boyut, uzantı ve gerçek içerik."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.uploads import UploadPath, UploadValidator

PDF = b"%PDF-1.7\n" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100

validate = UploadValidator(1, ("pdf", "png"))


def upload(name: str, content: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


def test_valid_file_passes():
    validate(upload("teklif.pdf", PDF))
    validate(upload("ekran.PNG", PNG))  # uzantı büyük harf olabilir


def test_unsupported_extension_rejected():
    with pytest.raises(ValidationError) as error:
        validate(upload("betik.sh", PDF))
    assert error.value.code == "extension"


def test_too_large_file_rejected():
    with pytest.raises(ValidationError) as error:
        validate(upload("buyuk.pdf", b"%PDF-1.7" + b"0" * (1024 * 1024)))
    assert error.value.code == "size"


def test_content_must_match_extension():
    """Uzantısı pdf ama içeriği başka olan dosya (ör. yeniden adlandırılmış betik) reddedilir."""
    with pytest.raises(ValidationError) as error:
        validate(upload("sahte.pdf", b"#!/bin/sh\nrm -rf /"))
    assert error.value.code == "content"


def test_validated_file_can_still_be_read():
    """Doğrulama dosya imlecini başa sarar; kayıt sırasında içerik eksiksiz yazılır."""
    file = upload("teklif.pdf", PDF)
    validate(file)
    assert file.read() == PDF


def test_upload_path_hides_original_name():
    path = UploadPath("private/inquiries")(None, "Gizli Teklif.PDF")
    assert path.startswith("private/inquiries/")
    assert path.endswith(".pdf")
    assert "gizli" not in path.lower()
    assert UploadPath("private/inquiries") == UploadPath("private/inquiries")  # migration'da sabit
