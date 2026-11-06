/* IterTrack logo mark — shared by the sidebar logo and the collapsed topbar. */
export function Mark({ decorative = false }: { decorative?: boolean }) {
  return (
    <svg
      className="mark"
      viewBox="380 355 1210 1200"
      {...(decorative
        ? { 'aria-hidden': true }
        : { role: 'img', 'aria-label': 'IterTrack' })}
    >
      <path className="m3" d="M390 752C385 590 500 465 665 465H1200L900 752Z" />
      <path
        className="m2"
        d="M572 1540V1420C572 1100 650 880 790 750C900 630 1010 540 1145 465C1280 405 1420 368 1572 365C1578 420 1578 460 1575 500C1550 640 1440 750 1300 752H1240C1170 760 1125 810 1120 880V1250C1120 1420 1000 1540 860 1540Z"
      />
      <path
        className="m1"
        d="M572 1540V1420C572 1100 650 880 790 750C900 630 1010 540 1145 465C1280 405 1420 368 1572 365C1578 420 1578 460 1575 500C1300 500 1000 640 880 860C770 1050 712 1250 710 1540Z"
      />
    </svg>
  );
}
