#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
/* Cage currently creates both cursor managers with a NULL theme and size 24.
 * Override only Cage's cursor managers, leaving other processes untouched. */
struct wlr_xcursor_manager;
struct wlr_xcursor_manager *wlr_xcursor_manager_create(const char *name, unsigned size) {
    typedef struct wlr_xcursor_manager *(*Create)(const char *, unsigned);
    Create original = (Create)dlsym(RTLD_NEXT, "wlr_xcursor_manager_create");
    if (!original) return NULL;
    char executable[4096];
    ssize_t n = readlink("/proc/self/exe", executable, sizeof(executable)-1);
    if (n > 0) {
        executable[n] = '\0';
        const char *base = strrchr(executable, '/');
        if (base && strcmp(base, "/cage") == 0) {
            name = "GoogleDot-Black";
            size = 20;
            fprintf(stderr, "ReGreet Cage cursor: %s size %u\n", name, size);
        }
    }
    return original(name, size);
}
