#include <gtk/gtk.h>
#include <string.h>
#ifndef MIME
#define MIME "application/x-lepton-schematic"
#endif
static int calls;
static void get(GtkClipboard *cb, GtkSelectionData *data, guint info, gpointer user) {
  const char *payload = "v 20220529 2\nC 100 100 1 0 0 resistor-1.sym\n";
  ++calls;
  gtk_selection_data_set(data, gdk_atom_intern(MIME,FALSE),8,(const guchar*)payload,strlen(payload));
}
static void clear(GtkClipboard *cb, gpointer user) {}
int main(int argc, char **argv) {
 gtk_init(&argc,&argv);
 GtkClipboard *cb=gtk_clipboard_get(GDK_SELECTION_CLIPBOARD);
 GtkTargetEntry target={MIME,0,1};
 gboolean ok=gtk_clipboard_set_with_data(cb,&target,1,get,clear,NULL);
 gtk_clipboard_set_can_store(cb,NULL,0);
 if(argc>1) gtk_clipboard_store(cb);
 GtkSelectionData *data=gtk_clipboard_wait_for_contents(cb,gdk_atom_intern(MIME,FALSE));
 const guchar *payload=data?gtk_selection_data_get_data(data):NULL;
 int len=data?gtk_selection_data_get_length(data):-1;
 g_print("set=%d callbacks=%d length=%d data=%s\n",ok,calls,len,payload?(const char*)payload:"NULL");
 if(data) gtk_selection_data_free(data);
 return payload && len>0 ? 0:1;
}
