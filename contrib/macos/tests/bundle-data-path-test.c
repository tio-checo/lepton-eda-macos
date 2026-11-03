#include <glib.h>
extern const gchar * const *eda_get_system_data_dirs(void);
extern const gchar * const *eda_get_system_config_dirs(void);
int main(int argc,char **argv) {
  g_assert_cmpint(argc,==,2);
  const gchar * const *data=eda_get_system_data_dirs();
  const gchar * const *config=eda_get_system_config_dirs();
  const char *override=g_getenv("LEPTON_DATA_DIR");
  if(override && g_path_is_absolute(override)) {
    g_assert_cmpstr(data[0],==,override); g_assert_null(data[1]);
    g_assert_cmpstr(config[0],==,override); g_assert_null(config[1]);
  } else {
    unsigned i=0; while(data[i+1]) ++i; g_assert_cmpstr(data[i],==,argv[1]);
    i=0; while(config[i+1]) ++i; g_assert_cmpstr(config[i],==,argv[1]);
  }
  g_assert_true(data==eda_get_system_data_dirs());
  g_assert_true(config==eda_get_system_config_dirs());
  g_print("PASS: data/config override or compiled fallback and cached directory arrays\n");
}
