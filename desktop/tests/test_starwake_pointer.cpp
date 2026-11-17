// Desktop integration test: run with the Starwake helper in LD_PRELOAD.
// Opens a temporary fullscreen surface, then verifies compositor activation and release.
#include <QGuiApplication>
#include <QQuickWindow>
#include <QQuickItem>
#include <QTimer>
#include <cstdio>
int main(int argc, char **argv) {
    QGuiApplication app(argc,argv);
    QQuickWindow window;
    window.setTitle("Starwake confinement test");
    QQuickItem arena(window.contentItem());
    arena.setObjectName("starwakeArena");
    arena.setProperty("capturePointer",false);
    window.showFullScreen();
    window.requestActivate();
    auto check = [&](bool expected) {
        if (window.contentItem()->property("starwakeConfined").toBool() != expected) {
            std::fprintf(stderr,"FAIL: expected confinement=%d\n",expected);
            app.exit(1); return false;
        }
        return true;
    };
    QTimer::singleShot(700,&app,[&]{arena.setProperty("capturePointer",true);});
    QTimer::singleShot(1300,&app,[&]{if(check(true)) arena.setProperty("capturePointer",false);});
    QTimer::singleShot(1550,&app,[&]{if(check(false)) arena.setProperty("capturePointer",true);});
    QTimer::singleShot(1900,&app,[&]{if(check(true)) arena.setProperty("capturePointer",false);});
    QTimer::singleShot(2150,&app,[&]{if(check(false)){std::puts("Starwake native confinement, pause release, resume and end release: PASS");app.quit();}});
    QTimer::singleShot(5000,&app,[&]{app.exit(2);});
    return app.exec();
}
