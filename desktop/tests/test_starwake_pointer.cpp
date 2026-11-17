// Desktop integration test: run with the Starwake helper in LD_PRELOAD.
// Opens a temporary fullscreen surface, then verifies compositor activation and release.
#include <QGuiApplication>
#include <QQuickWindow>
#include <QQuickItem>
#include <QTimer>
#include <QCursor>
#include <QTabletEvent>
#include <QPointingDevice>
#include <cstdio>
int main(int argc, char **argv) {
    QGuiApplication app(argc,argv);
    QQuickWindow window;
    window.setTitle("Starwake confinement test");
    QQuickItem arena(window.contentItem());
    arena.setObjectName("starwakeArena");
    arena.setProperty("capturePointer",false);
    QGuiApplication::setOverrideCursor(QCursor(Qt::WaitCursor));
    window.showFullScreen();
    window.requestActivate();
    auto check = [&](bool expected) {
        const auto *cursor = QGuiApplication::overrideCursor();
        if (!cursor || cursor->shape() != (expected ? Qt::BlankCursor : Qt::WaitCursor)) {
            std::fprintf(stderr,"FAIL: cursor not hidden/restored with capture=%d\n",expected);
            app.exit(1); return false;
        }
        if (window.contentItem()->property("starwakeConfined").toBool() != expected) {
            std::fprintf(stderr,"FAIL: expected confinement=%d\n",expected);
            app.exit(1); return false;
        }
        return true;
    };
    QTimer::singleShot(700,&app,[&]{arena.setProperty("capturePointer",true);});
    QTimer::singleShot(1100,&app,[&]{
        QPointingDevice pen("Test stylus",42,QInputDevice::DeviceType::Stylus,QPointingDevice::PointerType::Pen,QInputDevice::Capability::Position,1,1);
        QTabletEvent event(QEvent::TabletMove,&pen,QPointF(100,100),QPointF(100,100),0,0,0,0,0,0,Qt::NoModifier,Qt::NoButton,Qt::NoButton);
        QCoreApplication::sendEvent(&window,&event);
        check(true);
    });
    QTimer::singleShot(1300,&app,[&]{if(check(true)) arena.setProperty("capturePointer",false);});
    QTimer::singleShot(1550,&app,[&]{if(check(false)) arena.setProperty("capturePointer",true);});
    QTimer::singleShot(1900,&app,[&]{if(check(true)) arena.setProperty("capturePointer",false);});
    QTimer::singleShot(2150,&app,[&]{if(check(false)){std::puts("Starwake confinement, stylus cursor hiding, cursor-stack restoration, pause/resume and end release: PASS");app.quit();}});
    QTimer::singleShot(5000,&app,[&]{app.exit(2);});
    return app.exec();
}
