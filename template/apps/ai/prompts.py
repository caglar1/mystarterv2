SUMMARY_SYSTEM = (
    "Sen Türkçe yazan, net ve tarafsız bir editörsün. Kullanıcının verdiği metni özetle. "
    "Yalnızca özeti yaz; giriş cümlesi, başlık veya yorum ekleme."
)

SUMMARY_LENGTHS = {
    "kisa": "2-3 cümlelik kısa bir paragrafla",
    "orta": "en fazla 5 madde işaretiyle",
    "uzun": "başlıklara ayrılmış, ayrıntılı ama gereksiz tekrar içermeyen bir özetle",
}


def summary_prompt(text: str, length: str) -> str:
    return f"Aşağıdaki metni {SUMMARY_LENGTHS[length]} özetle.\n\n<metin>\n{text}\n</metin>"
