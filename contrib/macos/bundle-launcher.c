/* Relocatable embedded-Guile launcher for the macOS development distribution. */
#include <libguile.h>
#include <mach-o/dyld.h>
#include <sys/stat.h>
#include <pwd.h>
#include <unistd.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <locale.h>
static char resources[PATH_MAX], frameworks[PATH_MAX], profile[PATH_MAX];
static void path_env(const char *key, const char *base, const char *suffix) {
  char value[PATH_MAX];
  if (snprintf(value, sizeof value, "%s/%s", base, suffix) >= sizeof value) exit(2);
  setenv(key, value, 1);
}
static void mkdirs(const char *path) {
  char copy[PATH_MAX];
  snprintf(copy, sizeof copy, "%s", path);
  for (char *p=copy+1; *p; ++p) if (*p=='/') { *p=0; mkdir(copy,0700); *p='/'; }
  mkdir(copy,0700);
}
static void pixbuf_cache(void) {
  char source[PATH_MAX], dest[PATH_MAX], temp[PATH_MAX];
  snprintf(source,sizeof source,"%s/pixbuf-loaders.cache.in",resources);
  snprintf(dest,sizeof dest,"%s/cache/pixbuf-loaders.cache",profile);
  snprintf(temp,sizeof temp,"%s/cache/pixbuf-XXXXXX",profile);
  FILE *in=fopen(source,"r"); int fd=mkstemp(temp);
  if(!in || fd<0) { perror("pixbuf cache"); exit(2); }
  FILE *out=fdopen(fd,"w"); char *line=NULL; size_t cap=0;
  const char *token="@BUNDLE_RESOURCES@";
  while(getline(&line,&cap,in)>=0) {
    char *p=line, *match;
    while((match=strstr(p,token))) {
      fwrite(p,1,(size_t)(match-p),out); fputs(resources,out); p=match+strlen(token);
    }
    fputs(p,out);
  }
  free(line); fclose(in); fclose(out);
  if(rename(temp,dest)) { perror("pixbuf cache rename"); exit(2); }
  setenv("GDK_PIXBUF_MODULE_FILE",dest,1);
}
static void inner(void *data, int argc, char **argv) {
  (void)data;
  scm_c_define("%bundle-resources", scm_from_utf8_string(resources));
  scm_c_eval_string("(set! %load-path (list (string-append %bundle-resources \"/share/lepton-eda/scheme\") (string-append %bundle-resources \"/share/guile/3.0\"))) (set! %load-compiled-path (list (string-append %bundle-resources \"/lib/guile/3.0/ccache\")))");
  scm_shell(argc, argv);
}
int main(int argc, char **argv) {
  char executable[PATH_MAX], real[PATH_MAX], contents[PATH_MAX];
  uint32_t size=sizeof executable;
  if (_NSGetExecutablePath(executable,&size) || !realpath(executable,real)) return 2;
  char *slash=strrchr(real,'/'); if (!slash) return 2; *slash=0;
  slash=strrchr(real,'/'); if (!slash) return 2; *slash=0;
  snprintf(contents,sizeof contents,"%s",real);
  snprintf(resources,sizeof resources,"%s/Resources",contents);
  snprintf(frameworks,sizeof frameworks,"%s/Frameworks",contents);
  const char *override=getenv("LEPTON_BUNDLE_PROFILE");
  struct passwd *pw=getpwuid(getuid());
  if (override && override[0]=='/') snprintf(profile,sizeof profile,"%s",override);
  else if (pw) snprintf(profile,sizeof profile,"%s/Library/Application Support/LeptonEDA-Quartz",pw->pw_dir);
  else return 2;
  const char *dirs[]={"config","cache","data"};
  mkdirs(profile);
  for(unsigned i=0;i<3;++i) { char p[PATH_MAX]; snprintf(p,sizeof p,"%s/%s",profile,dirs[i]); mkdirs(p); }
  setlocale(LC_ALL,"");
  setenv("LEPTON_BUNDLE_RESOURCES",resources,1);
  path_env("LEPTON_DATA_DIR",resources,"share/lepton-eda");
  path_env("XDG_CONFIG_HOME",profile,"config");
  path_env("XDG_CACHE_HOME",profile,"cache");
  path_env("XDG_DATA_HOME",profile,"data");
  path_env("XDG_DATA_DIRS",resources,"share");
  path_env("XDG_CONFIG_DIRS",resources,"share");
  path_env("GSETTINGS_SCHEMA_DIR",resources,"share/glib-2.0/schemas");
  path_env("GTK_PATH",resources,"lib/gtk-3.0");
  setenv("GTK_EXE_PREFIX",resources,1);
  path_env("GDK_PIXBUF_MODULEDIR",resources,"lib/gdk-pixbuf-2.0/2.10.0/loaders");
  pixbuf_cache();
  path_env("GUILE_LOAD_PATH",resources,"share/guile/3.0");
  path_env("GUILE_LOAD_COMPILED_PATH",resources,"lib/guile/3.0/ccache");
  path_env("GUILE_SYSTEM_EXTENSIONS_PATH",resources,"lib/guile/3.0/extensions");
  setenv("GUILE_EXTENSIONS_PATH",frameworks,1);
  setenv("LTDL_LIBRARY_PATH",frameworks,1);
  path_env("LIBLEPTON",frameworks,"liblepton.dylib");
  path_env("LIBLEPTONGUI",frameworks,"libleptongui.dylib");
  path_env("PATH",resources,"bin:/usr/bin:/bin:/usr/sbin:/sbin");
  setenv("GDK_BACKEND","quartz",1);
  setenv("GUILE_AUTO_COMPILE","0",1);
  unsetenv("DISPLAY"); unsetenv("GTK_MODULES");
  unsetenv("LEPTON_INHIBIT_RC_FILES"); unsetenv("LEPTON_SCM_PRECOMPILE");
  const char *tool="schematic";
  int first=1;
  if (argc>=3 && !strcmp(argv[1],"--tool")) { tool=argv[2]; first=3; }
  const char *allowed[]={"schematic","export","netlist","shell","config","cli"};
  int valid=0;
  for(unsigned i=0;i<6;++i) if (!strcmp(tool,allowed[i])) valid=1;
  if(!valid) { fprintf(stderr,"Unknown bundled tool: %s\n",tool); return 2; }
  int gui = first==1;
  if (gui) {
    char log[PATH_MAX]; snprintf(log,sizeof log,"%s/editor.log",profile);
    freopen(log,"a",stdout); freopen(log,"a",stderr);
    fprintf(stderr,"BUNDLE_START resources=%s profile=%s\n",resources,profile);
    /* Documents passed explicitly are made absolute before changing cwd. */
    for(int i=first;i<argc;++i) if(argv[i][0]!='-') {
      char full[PATH_MAX]; if(realpath(argv[i],full)) argv[i]=strdup(full);
    }
    if(chdir(profile)) return 2;
  }
  char script[PATH_MAX]; snprintf(script,sizeof script,"%s/entry/lepton-%s.scm",resources,tool);
  char **args=calloc((size_t)argc+4,sizeof(char*));
  args[0]="LeptonEDA"; args[1]="-s"; args[2]=script;
  int count=3;
  for(int i=first;i<argc;++i) if(strncmp(argv[i],"-psn_",5)) args[count++]=argv[i];
  scm_boot_guile(count,args,inner,NULL);
  return 0;
}
