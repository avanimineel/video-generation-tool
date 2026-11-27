import React from 'react';

interface PaperCast {
  style?: string;
  action?: string;
}

interface LookEffectProps {
  effect: string;
  width: number;
  height: number;
  time: number;
  subject?: string;
  badge?: boolean;
  place?: string;
  cast?: PaperCast[];
  props?: string[];
}

const BITS = [0.08, 0.17, 0.29, 0.41, 0.53, 0.66, 0.74, 0.88, 0.13, 0.37, 0.61, 0.82];

function PaperPerson({ style, action, left, foot, tall }: { style: string; action: string; left: number; foot: number; tall: number }) {
  const height = style === 'girl' || style === 'boy' ? tall * 0.72 : style === 'elder' ? tall * 0.86 : tall;
  const body = style === 'woman' || style === 'girl' ? '#BFE3DC' : '#9060DE';
  const hair = style === 'elder' ? '#FFFCF8' : '#9060DE';
  const head = height * 0.22;
  return (
    <div style={{ position: 'absolute', left, bottom: foot, width: height * 0.46, height }}>
      <div style={{ position: 'absolute', left: '28%', top: 0, width: head, height: head, borderRadius: '50%', background: '#F5DCB8', boxShadow: `0 ${-head * 0.35}px 0 ${head * 0.15}px ${hair}` }} />
      <div style={{ position: 'absolute', left: '18%', top: head * 0.85, width: '64%', height: height * 0.38, borderRadius: 8, background: body }} />
      {action === 'wave' && <div style={{ position: 'absolute', right: -height * 0.08, top: head * 0.2, width: height * 0.08, height: height * 0.28, borderRadius: 6, background: body, transform: 'rotate(-28deg)' }} />}
      {action === 'offer' && <div style={{ position: 'absolute', left: -height * 0.12, top: head, width: height * 0.28, height: height * 0.08, borderRadius: 6, background: body }} />}
      {action === 'pray' && <div style={{ position: 'absolute', left: '40%', top: head * 1.1, width: height * 0.1, height: height * 0.16, borderRadius: 6, background: body }} />}
      {action === 'walk' ? (
        <div style={{ position: 'absolute', left: '22%', top: height * 0.55, width: '56%', height: height * 0.4, background: body, clipPath: 'polygon(20% 0, 40% 0, 70% 100%, 10% 100%)' }} />
      ) : action === 'sit' ? (
        <div style={{ position: 'absolute', left: '8%', top: height * 0.62, width: '84%', height: height * 0.12, borderRadius: 6, background: body }} />
      ) : (
        <>
          <div style={{ position: 'absolute', left: '28%', top: height * 0.58, width: '14%', height: height * 0.4, background: body }} />
          <div style={{ position: 'absolute', left: '56%', top: height * 0.58, width: '14%', height: height * 0.4, background: body }} />
        </>
      )}
    </div>
  );
}

export const LookEffect: React.FC<LookEffectProps> = ({ effect, width, height, time, subject = '', badge = false, place = '', cast = [], props = [] }) => {
  const box: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    width,
    height,
    pointerEvents: 'none',
    zIndex: 16,
    overflow: 'hidden',
  };
  if (effect === 'camera') {
    const arm = Math.max(18, width * 0.08);
    const mark = (left: number, top: number, flipX: boolean, flipY: boolean): React.CSSProperties => ({
      position: 'absolute',
      left,
      top,
      width: arm,
      height: arm,
      borderColor: 'rgba(255,255,255,0.9)',
      borderStyle: 'solid',
      borderTopWidth: flipY ? 0 : 3,
      borderBottomWidth: flipY ? 3 : 0,
      borderLeftWidth: flipX ? 0 : 3,
      borderRightWidth: flipX ? 3 : 0,
    });
    return (
      <div style={box}>
        <div style={mark(width * 0.05, height * 0.05, false, false)} />
        <div style={mark(width * 0.95 - arm, height * 0.05, true, false)} />
        <div style={mark(width * 0.05, height * 0.95 - arm, false, true)} />
        <div style={mark(width * 0.95 - arm, height * 0.95 - arm, true, true)} />
        <div style={{ position: 'absolute', left: width / 2 - 10, top: height / 2 - 10, width: 20, height: 20, border: '2px solid rgba(255,255,255,0.75)', borderRadius: '50%' }} />
        <div style={{ position: 'absolute', left: width * 0.07, top: height * 0.08, width: 10, height: 10, borderRadius: '50%', background: '#e11d2e' }} />
      </div>
    );
  }
  if (effect === 'confetti') {
    return (
      <div style={box}>
        {BITS.map((seed, index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              left: (seed * width + index * 17) % width,
              top: ((seed * height + time * 40) % height),
              width: index % 3 === 0 ? 5 : 8,
              height: index % 2 === 0 ? 12 : 7,
              background: ['#f5d000', '#ff4d8d', '#49c6ff', '#9dffb0', '#fff'][index % 5],
              transform: `rotate(${(index * 24) % 80}deg)`,
              opacity: 0.9,
            }}
          />
        ))}
      </div>
    );
  }
  if (effect === 'paper') {
    return (
      <div style={{ ...box, background: 'rgba(214,196,160,0.28)', boxShadow: 'inset 0 0 40px rgba(90,60,30,0.25)' }}>
        {[0.2, 0.38, 0.55, 0.72].map((y) => (
          <div key={y} style={{ position: 'absolute', left: 0, top: height * y, width, height: 1, background: 'rgba(110,80,40,0.45)', transform: 'rotate(-2deg)' }} />
        ))}
      </div>
    );
  }
  if (effect === 'fog') {
    return <div style={{ ...box, background: 'linear-gradient(to top, rgba(230,236,240,0.72), rgba(230,236,240,0.18) 42%, transparent 68%)' }} />;
  }
  if (effect === 'film') {
    const bar = height * 0.07;
    return (
      <div style={box}>
        <div style={{ position: 'absolute', left: 0, top: 0, width, height: bar, background: '#000' }} />
        <div style={{ position: 'absolute', left: 0, bottom: 0, width, height: bar, background: '#000' }} />
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'radial-gradient(rgba(255,255,255,0.35) 0.6px, transparent 0.6px)', backgroundSize: '7px 9px', opacity: 0.35 }} />
      </div>
    );
  }
  if (effect === 'streaming') {
    return (
      <div style={{ ...box, border: '3px solid rgba(255,255,255,0.85)' }}>
        <div style={{ position: 'absolute', left: 0, top: height * 0.84, width: width * 0.55, height: height * 0.08, background: 'rgba(0,0,0,0.55)' }} />
      </div>
    );
  }
  if (effect === 'glitch') {
    return (
      <div style={box}>
        {[0.18, 0.41, 0.63].map((y, index) => (
          <div key={y} style={{ position: 'absolute', left: index === 1 ? -8 : 6, top: height * y, width, height: 8 + index * 4, background: index === 1 ? 'rgba(0,230,255,0.45)' : 'rgba(255,0,90,0.4)' }} />
        ))}
      </div>
    );
  }
  if (effect === 'storm') {
    const flash = Math.floor(time * 3) % 5 === 0;
    return (
      <div style={{ ...box, background: 'linear-gradient(to bottom, rgba(8,14,32,0.55), transparent 34%)' }}>
        {BITS.map((seed, index) => (
          <div key={index} style={{ position: 'absolute', left: (seed * width) % width, top: (seed * height + time * 80) % height, width: 1, height: 16, background: 'rgba(200,220,255,0.7)', transform: 'rotate(18deg)' }} />
        ))}
        {flash && <div style={{ position: 'absolute', left: width * 0.58, top: 0, width: 3, height: height * 0.55, background: 'rgba(255,255,255,0.9)', transform: 'skewX(-18deg)' }} />}
      </div>
    );
  }
  if (effect === 'light_leak') {
    return (
      <div style={{ ...box, background: 'radial-gradient(circle at 8% 0%, rgba(255,150,40,0.55), transparent 42%), radial-gradient(circle at 100% 100%, rgba(255,50,90,0.35), transparent 46%)' }} />
    );
  }
  if (effect === 'flat_vector') {
    const rise = (time * 8) % 8;
    return (
      <div style={{ ...box, background: 'rgba(236,228,210,0.35)' }}>
        <div style={{ position: 'absolute', left: width * 0.1, top: height * 0.2 + rise, width: width * 0.16, height: width * 0.16, borderRadius: '50%', background: '#148c96' }} />
        <div style={{ position: 'absolute', left: width * 0.32, top: height * 0.24, width: width * 0.24, height: height * 0.1, background: '#e65a46' }} />
        {[0.22, 0.38, 0.16].map((level, index) => (
          <div key={level} style={{ position: 'absolute', left: width * (0.66 + index * 0.08), top: height * (0.42 - level), width: width * 0.06, height: height * level, background: '#1e325a' }} />
        ))}
      </div>
    );
  }
  if (effect === 'scrapbook') {
    return (
      <div style={box}>
        <div style={{ position: 'absolute', left: width * 0.08, top: height * 0.14, width: width * 0.48, height: height * 0.46, background: '#fffdf6', boxShadow: '6px 8px 0 rgba(40,30,20,0.25)' }} />
        <div style={{ position: 'absolute', left: width * 0.14, top: height * 0.22, width: width * 0.36, height: height * 0.28, background: '#b4c8be' }} />
        <div style={{ position: 'absolute', left: width * 0.16, top: height * 0.1, width: width * 0.16, height: height * 0.045, background: 'rgba(170,210,160,0.85)' }} />
        <div style={{ position: 'absolute', left: width * 0.58, top: height * 0.62, width: width * 0.2, height: height * 0.08, background: '#ffd678', transform: 'rotate(8deg)' }} />
      </div>
    );
  }
  if (effect === 'flat_infographic') {
    return (
      <div style={box}>
        <div style={{ position: 'absolute', left: width * 0.42, top: height * 0.16, width: width * 0.5, height: height * 0.6, background: 'rgba(255,255,255,0.92)' }}>
          <div style={{ position: 'absolute', left: width * 0.04, top: height * 0.06, width: width * 0.08, height: width * 0.08, borderRadius: '50%', background: '#148c96' }} />
          {[0.34, 0.22, 0.28].map((span, index) => (
            <div key={span} style={{ position: 'absolute', left: width * 0.04, top: height * (0.2 + index * 0.1), width: width * span, height: height * 0.045, background: ['#e65a46', '#1e325a', '#f0b428'][index] }} />
          ))}
        </div>
      </div>
    );
  }
  if (effect === 'paper_purple') {
    const drift = Math.sin(time * 0.8) * width * 0.012;
    if (badge) {
      return (
        <div style={box}>
          <div style={{ position: 'absolute', left: width * 0.08, top: height * 0.86, width: width * 0.18, height: height * 0.08, borderRadius: 10, background: '#9060DE', boxShadow: '4px 4px 0 rgba(79,73,71,0.18)' }} />
          <div style={{ position: 'absolute', left: width * 0.1, top: height * 0.875, width: 12, height: 12, borderRadius: '50%', background: '#BFE3DC' }} />
        </div>
      );
    }
    const shape = subject || 'object';
    const people = (cast || []).filter(member => member && member.style).slice(0, 2);
    if (people.length) {
      const spots = people.length === 1 ? [width * 0.38] : [width * 0.22, width * 0.52];
      return (
        <div style={{ ...box, background: '#F5EFEC' }}>
          <div style={{ position: 'absolute', left: 0, top: height * 0.78, width, height: height * 0.22, background: '#E6E5EB' }} />
          {place === 'house' && (
            <div style={{ position: 'absolute', left: width * 0.3 + drift, top: height * 0.28, width: width * 0.4, height: height * 0.42 }}>
              <div style={{ position: 'absolute', left: '10%', right: '10%', top: '38%', bottom: 0, background: '#BFE3DC' }} />
              <div style={{ position: 'absolute', left: '4%', top: '8%', width: 0, height: 0, borderLeft: `${width * 0.16}px solid transparent`, borderRight: `${width * 0.16}px solid transparent`, borderBottom: `${height * 0.14}px solid #9060DE` }} />
            </div>
          )}
          {props.includes('chair') && <div style={{ position: 'absolute', right: width * 0.12, top: height * 0.58, width: width * 0.12, height: height * 0.16, border: '6px solid #9060DE', borderBottom: 'none', background: '#FFFCF8' }} />}
          {people.map((member, index) => (
            <PaperPerson key={`${member.style}-${index}`} style={String(member.style)} action={String(member.action || 'stand')} left={spots[index] + drift} foot={height * 0.22} tall={height * 0.42} />
          ))}
        </div>
      );
    }
    return (
      <div style={{ ...box, background: '#F5EFEC' }}>
        <div style={{ position: 'absolute', left: 0, top: height * 0.78, width, height: height * 0.22, background: '#E6E5EB' }} />
        <div style={{ position: 'absolute', left: width * 0.28 + drift, top: height * 0.34, width: width * 0.44, height: height * 0.38, transformOrigin: 'center' }}>
          {shape === 'book' && (
            <div style={{ position: 'absolute', inset: 0, borderRadius: 16, background: '#9060DE', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)' }}>
              <div style={{ position: 'absolute', left: '12%', top: '10%', right: '10%', bottom: '10%', borderRadius: 8, background: '#FFFCF8' }} />
              <div style={{ position: 'absolute', right: '6%', top: 0, width: '14%', height: '28%', background: '#BFE3DC' }} />
            </div>
          )}
          {shape === 'bill' && (
            <div style={{ position: 'absolute', left: 0, right: 0, top: '12%', bottom: '12%', borderRadius: 14, background: '#FFFCF8', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '16%', background: '#9060DE' }} />
              <div style={{ position: 'absolute', left: '28%', top: '28%', right: '12%', height: 10, background: '#BFE3DC' }} />
            </div>
          )}
          {shape === 'phone' && (
            <div style={{ position: 'absolute', left: '18%', right: '18%', top: '-8%', bottom: '-6%', borderRadius: 28, background: '#9060DE', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)' }}>
              <div style={{ position: 'absolute', left: '8%', right: '8%', top: '8%', bottom: '10%', borderRadius: 16, background: '#FFFCF8' }} />
              <div style={{ position: 'absolute', left: '42%', bottom: '4%', width: '16%', height: 8, borderRadius: 8, background: '#BFE3DC' }} />
            </div>
          )}
          {shape === 'house' && (
            <div style={{ position: 'absolute', inset: 0 }}>
              <div style={{ position: 'absolute', left: '10%', right: '10%', top: '38%', bottom: 0, background: '#BFE3DC', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)' }} />
              <div style={{ position: 'absolute', left: '4%', top: '8%', width: 0, height: 0, borderLeft: `${width * 0.18}px solid transparent`, borderRight: `${width * 0.18}px solid transparent`, borderBottom: `${height * 0.16}px solid #9060DE` }} />
            </div>
          )}
          {shape === 'calendar' && (
            <div style={{ position: 'absolute', inset: 0, borderRadius: 16, background: '#FFFCF8', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)', overflow: 'hidden' }}>
              <div style={{ height: '18%', background: '#9060DE' }} />
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, padding: 10 }}>
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} style={{ height: height * 0.045, borderRadius: 4, background: index % 2 ? '#9060DE' : '#BFE3DC' }} />
                ))}
              </div>
            </div>
          )}
          {(shape === 'object' || shape === 'heart' || shape === 'pill' || shape === 'cup') && (
            <div style={{ position: 'absolute', inset: 0, borderRadius: shape === 'pill' ? 999 : '46% 54% 48% 52%', background: '#9060DE', boxShadow: '8px 10px 0 rgba(79,73,71,0.16)' }}>
              <div style={{ position: 'absolute', left: '30%', top: '32%', width: '40%', height: '36%', borderRadius: 10, background: '#BFE3DC' }} />
            </div>
          )}
        </div>
      </div>
    );
  }
  if (effect === 'paper_craft') {
    return (
      <div style={box}>
        <div style={{ position: 'absolute', left: width * 0.24, top: height * 0.3, width: width * 0.48, height: height * 0.42, borderRadius: '46% 54% 48% 52%', background: 'rgba(40,30,20,0.28)' }} />
        <div style={{ position: 'absolute', left: width * 0.22, top: height * 0.28, width: width * 0.48, height: height * 0.42, borderRadius: '46% 54% 48% 52%', background: '#e8d6b8' }} />
        <div style={{ position: 'absolute', left: width * 0.34, top: height * 0.32, width: 0, height: 0, borderLeft: `${width * 0.12}px solid transparent`, borderRight: `${width * 0.12}px solid transparent`, borderBottom: `${height * 0.14}px solid #c45c4a` }} />
        <div style={{ position: 'absolute', left: width * 0.4, top: height * 0.48, width: width * 0.12, height: height * 0.16, background: '#46828c' }} />
      </div>
    );
  }
  return (
    <div style={{ ...box, background: 'radial-gradient(circle at 50% 40%, rgba(8,10,30,0.15), rgba(6,8,28,0.55))' }}>
      {BITS.map((seed, index) => (
        <div key={index} style={{ position: 'absolute', left: (seed * width * 1.3) % width, top: (seed * height * 1.7) % height, width: index % 4 === 0 ? 3 : 2, height: index % 4 === 0 ? 3 : 2, borderRadius: '50%', background: '#fff', opacity: (Math.floor(time * 2) + index) % 5 === 0 ? 0.35 : 1 }} />
      ))}
    </div>
  );
};
