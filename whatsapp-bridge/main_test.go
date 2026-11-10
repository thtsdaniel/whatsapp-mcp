package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestSafeMediaFilename(t *testing.T) {
	cases := []struct {
		name, messageID, filename, want string
	}{
		{"plain name", "ABC123", "report.pdf", "ABC123_report.pdf"},
		{"traversal is reduced to the base name", "ABC123", "../../etc/passwd", "ABC123_passwd"},
		{"absolute path is reduced to the base name", "ABC123", "/etc/passwd", "ABC123_passwd"},
		{"empty name falls back to the message ID", "ABC123", "", "ABC123_media_ABC123"},
		{"dot-dot name falls back to the message ID", "ABC123", "..", "ABC123_media_ABC123"},
		{"message ID cannot carry a directory", "../ABC123", "a.jpg", "ABC123_a.jpg"},
		{"same-second photos get distinct names", "MSG1", "image_20261030_143000.jpg", "MSG1_image_20261030_143000.jpg"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := safeMediaFilename(c.messageID, c.filename)
			if got != c.want {
				t.Fatalf("safeMediaFilename(%q, %q) = %q, want %q", c.messageID, c.filename, got, c.want)
			}
			if strings.ContainsAny(got, `/\`) {
				t.Fatalf("result %q contains a path separator", got)
			}
		})
	}
}

func TestExtractDirectPathFromURL(t *testing.T) {
	cases := []struct{ name, in, want string }{
		{
			"signed query is kept",
			"https://mmg.whatsapp.net/v/t62.7118-24/file_n.enc?ccb=11-4&oh=abc&oe=def",
			"/v/t62.7118-24/file_n.enc?ccb=11-4&oh=abc&oe=def",
		},
		{
			"no query",
			"https://mmg.whatsapp.net/v/t62.7118-24/file_n.enc",
			"/v/t62.7118-24/file_n.enc",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := extractDirectPathFromURL(c.in); got != c.want {
				t.Fatalf("extractDirectPathFromURL(%q) = %q, want %q", c.in, got, c.want)
			}
		})
	}
}

func TestIsLoopbackHost(t *testing.T) {
	allowed := []string{"127.0.0.1:8080", "127.0.0.1", "localhost:8080", "localhost", "[::1]:8080"}
	refused := []string{"evil.example:8080", "evil.example", "192.168.1.20:8080", "127.0.0.1.evil.example:8080", ""}
	for _, h := range allowed {
		if !isLoopbackHost(h) {
			t.Errorf("isLoopbackHost(%q) = false, want true", h)
		}
	}
	for _, h := range refused {
		if isLoopbackHost(h) {
			t.Errorf("isLoopbackHost(%q) = true, want false", h)
		}
	}
}

// The guards run before the handler touches the WhatsApp client or the store,
// so nil is enough for both here.
func TestDownloadHandlerGuards(t *testing.T) {
	handler := downloadHandler(nil, nil)
	body := `{"message_id":"A","chat_jid":"B"}`

	cases := []struct {
		name, method, host, contentType, body string
		want                                  int
	}{
		{"rebinding host is refused", http.MethodPost, "evil.example:8080", "application/json", body, http.StatusForbidden},
		{"LAN address is refused", http.MethodPost, "192.168.1.20:8080", "application/json", body, http.StatusForbidden},
		{"GET is refused", http.MethodGet, "127.0.0.1:8080", "application/json", "", http.StatusMethodNotAllowed},
		{"form post from a browser is refused", http.MethodPost, "127.0.0.1:8080", "text/plain", body, http.StatusUnsupportedMediaType},
		{"missing content type is refused", http.MethodPost, "127.0.0.1:8080", "", body, http.StatusUnsupportedMediaType},
		{"malformed JSON is refused", http.MethodPost, "127.0.0.1:8080", "application/json", "{", http.StatusBadRequest},
		{"missing fields are refused", http.MethodPost, "127.0.0.1:8080", "application/json; charset=utf-8", `{}`, http.StatusBadRequest},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			req := httptest.NewRequest(c.method, "/api/download", strings.NewReader(c.body))
			req.Host = c.host
			if c.contentType != "" {
				req.Header.Set("Content-Type", c.contentType)
			}
			rec := httptest.NewRecorder()
			handler(rec, req)
			if rec.Code != c.want {
				t.Fatalf("status = %d, want %d", rec.Code, c.want)
			}
		})
	}
}
