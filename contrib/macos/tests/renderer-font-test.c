#include <glib-object.h>
#include <cairo.h>
#include <pango/pangocairo.h>
extern GObject *eda_renderer_new(cairo_t *, PangoContext *);
int main(void) {
  GObject *renderer = eda_renderer_new(NULL, NULL);
  const char *inputs[] = {"", NULL, "Serif 12", ""};
  const char *expected[] = {"Sans", "Sans", "Serif 12", "Sans"};
  for (unsigned i = 0; i < G_N_ELEMENTS(inputs); ++i) {
    gchar *font = NULL;
    g_object_set(renderer, "font-name", inputs[i], NULL);
    g_object_get(renderer, "font-name", &font, NULL);
    g_assert_cmpstr(font, ==, expected[i]);
    PangoFontDescription *desc = pango_font_description_from_string(font);
    PangoContext *pc = pango_font_map_create_context(pango_cairo_font_map_get_default());
    PangoFontMetrics *metrics = pango_context_get_metrics(pc, desc, NULL);
    g_assert_nonnull(metrics);
    pango_font_metrics_unref(metrics);
    g_object_unref(pc);
    pango_font_description_free(desc);
    g_free(font);
  }
  g_object_unref(renderer);
  g_print("PASS: empty/NULL font uses Sans; explicit family retained; CoreText metrics succeed\n");
}
