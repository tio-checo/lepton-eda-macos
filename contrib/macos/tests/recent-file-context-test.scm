;; Exercise the real recent-file callback without creating native GTK windows.
(use-modules (srfi srfi-64) (system foreign)
             (lepton toplevel) (lepton toplevel foreign)
             (schematic window) (schematic window foreign)
             (schematic window global))

(define runner (test-runner-simple))
(test-runner-current runner)
(test-begin "recent-file-context")
(define window-module (resolve-module '(schematic window)))
(define global-module (resolve-module '(schematic window global)))
(define target-window (make-pointer 1))
(define target-toplevel (make-pointer 2))
(define filename "/test/recent schematic.sch")
(define filename-pointer (string->pointer filename))
(define selected-page (list 'page))
(define opened? #f)
(define selected? #f)

;; Replace only native access and actual page loading. Keep the callback,
;; dynamic window/toplevel binding and pointer wrappers under test.
(module-set! global-module 'schematic_window_get_toplevel
             (lambda (window) target-toplevel))
(module-set! window-module 'schematic_menu_recent_chooser_get_filename
             (lambda (chooser window) filename-pointer))
(module-set! window-module 'g_free (lambda (pointer) #t))
(define (check-context)
  (test-equal "callback window" 1
              (pointer-address (window->pointer (current-window))))
  (test-equal "callback toplevel" 2
              (pointer-address (toplevel->pointer (current-toplevel)))))
(module-set! window-module 'window-open-page!
             (lambda (window path)
               (check-context)
               (test-equal "filename retained" filename path)
               (set! opened? #t)
               selected-page))
(module-set! window-module 'window-set-current-page!
             (lambda (window page)
               (check-context)
               (test-eq "opened page selected" selected-page page)
               (set! selected? #t)))
(define callback
  (module-ref window-module 'callback-recent-chooser-item-activated))
(with-fluids ((%lepton-window #f) (%lepton-toplevel #f))
  (callback %null-pointer target-window)
  (test-assert "document opened" opened?)
  (test-assert "document selected" selected?)
  (test-eq "previous window context restored" #f (fluid-ref %lepton-window))
  (test-eq "previous toplevel context restored" #f (fluid-ref %lepton-toplevel)))
(test-end "recent-file-context")
(exit (if (zero? (test-runner-fail-count runner)) 0 1))
