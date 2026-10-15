import React, {useEffect} from 'react';
import { BACKEND_ORIGIN } from '../../services/api';
import { MotionGraphicItem } from '../../types';

/** Inverse person matte hides only the background typography/cards; original video stays untouched. */
export function BehindSpeakerTitle({graphic,time,width,height}:{graphic:MotionGraphicItem,time:number,width:number,height:number}) {
  const p=graphic.parameters;
  const mask=p.subject_mask;
  useEffect(()=>{
    if (!mask?.prefix || !mask?.count) return;
    const images=Array.from({length:mask.count},(_,i)=>{const image=new Image();image.src=`${BACKEND_ORIGIN}${mask.prefix}${String(i).padStart(5,'0')}.png`;return image;});
    return ()=>images.forEach(image=>{image.onload=null;});
  },[mask?.prefix,mask?.count]);

  if (!mask?.prefix || !mask?.count) return null;

  const frame=Math.min(mask.count-1,Math.max(0,Math.floor((time-mask.start)*mask.fps)));
  const url=`${BACKEND_ORIGIN}${mask.prefix}${String(frame).padStart(5,'0')}.png`;
  const lines=Array.isArray(p.title_lines)?p.title_lines:[{text:p.headline||graphic.title,offset:0}];
  const exit=Math.min(1,Math.max(0,(graphic.end-time)/.2));
  const scale=graphic.scale??1;

  const isMixed = p.title_style === 'mixed_typography' || (p.setup_text && p.accent_text);
  const setupText = String(p.setup_text || (isMixed ? lines[0]?.text : '') || '').toUpperCase();
  const accentText = String(p.accent_text || (isMixed ? lines[1]?.text : '') || '');
  const accentColor = p.accent_color || '#E04F26';
  const setupColor = p.setup_color || '#FFFFFF';
  const boxRotation = Number(p.box_rotation ?? -3);
  const showBox = p.bounding_box_highlight !== false;

  const baseSize = Math.min(width * 0.088, width * 0.9 / Math.max(1, setupText.length * 0.5));
  const accentSize = baseSize * 1.25;

  const defaultTextStyle:React.CSSProperties={position:'absolute',left:`${graphic.pos_x*100}%`,top:`${graphic.pos_y*100}%`,width:'94%',transform:`translate(-50%,-50%) scale(${scale})`,textAlign:'center',fontFamily:'Impact, Arial Black, sans-serif',fontWeight:900,lineHeight:.96,letterSpacing:'-.035em'};

  return <div style={{position:'absolute',inset:0,width,height,pointerEvents:'none',zIndex:15}}>
    <div style={{position:'absolute',inset:0,maskImage:`url("${url}")`,WebkitMaskImage:`url("${url}")`,maskSize:'100% 100%',WebkitMaskSize:'100% 100%',maskRepeat:'no-repeat'}}>
      {/* 1. Mixed Typography behind speaker */}
      {isMixed ? (
        <div style={{
          position: 'absolute',
          left: `${graphic.pos_x * 100}%`,
          top: `${graphic.pos_y * 100}%`,
          width: '94%',
          transform: `translate(-50%, -50%) scale(${scale})`,
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: exit
        }}>
          {setupText && (
            <div style={{
              fontFamily: '"Arial Black", Impact, Inter, sans-serif',
              fontWeight: 900,
              fontSize: baseSize,
              color: setupColor,
              letterSpacing: '-0.035em',
              lineHeight: 1.05,
              textTransform: 'uppercase',
              textShadow: '0 2px 8px rgba(0,0,0,0.85)'
            }}>
              {setupText}
            </div>
          )}
          {accentText && (
            <div style={{ marginTop: setupText ? -baseSize * 0.18 : 0 }}>
              {showBox ? (
                <div style={{
                  position: 'relative',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: `2px solid ${accentColor}`,
                  transform: `rotate(${boxRotation}deg)`,
                  padding: '4px 12px'
                }}>
                  <span style={{ position: 'absolute', top: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                  <span style={{ position: 'absolute', top: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                  <span style={{ position: 'absolute', bottom: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                  <span style={{ position: 'absolute', bottom: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                  <span style={{
                    fontFamily: '"Georgia", Baskerville, "Playfair Display", serif',
                    fontStyle: 'italic',
                    fontWeight: 700,
                    fontSize: accentSize,
                    color: accentColor,
                    whiteSpace: 'nowrap',
                    lineHeight: 1.05,
                    textShadow: '0 2px 8px rgba(0,0,0,0.6)'
                  }}>
                    {accentText}
                  </span>
                </div>
              ) : (
                <span style={{
                  fontFamily: '"Georgia", Baskerville, "Playfair Display", serif',
                  fontStyle: 'italic',
                  fontWeight: 700,
                  fontSize: accentSize,
                  color: accentColor,
                  transform: `rotate(${boxRotation}deg)`,
                  display: 'inline-block',
                  lineHeight: 1.05
                }}>
                  {accentText}
                </span>
              )}
            </div>
          )}
        </div>
      ) : (
        /* 2. Standard behind_subject block typography */
        <div style={defaultTextStyle}>{lines.slice(0,2).map((line:any,i:number)=>{
          const progress=Math.min(1,Math.max(0,(time-graphic.start-Number(line.offset||0))/.3));
          return <div key={i} style={{color:'#fffaf1',fontSize:Math.min(width*.16,width*.94/Math.max(1,String(line.text).length*.55)),opacity:exit*progress,transform:`translateY(${(1-progress)*10}px)`}}>{line.text}</div>;
        })}</div>
      )}

      {/* 3. Tilted image cards behind speaker */}
      {Array.isArray(p.card_media) && p.card_media.length > 0 && (
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: exit }}>
          {p.card_media.slice(0, 3).map((card: any, i: number) => {
            const tilts = [-7, 7, -3];
            const lefts = ['10%', '65%', '38%'];
            const tops = ['20%', '24%', '55%'];
            return (
              <div
                key={card.url || i}
                style={{
                  position: 'absolute',
                  width: width * 0.28,
                  height: width * 0.22,
                  left: lefts[i],
                  top: tops[i],
                  transform: `rotate(${tilts[i]}deg)`,
                  border: showBox ? `2px solid ${accentColor}` : '2px solid white',
                  borderRadius: 4,
                  overflow: 'hidden',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.7)'
                }}
              >
                {showBox && (
                  <>
                    <span style={{ position: 'absolute', top: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor, zIndex: 10 }} />
                    <span style={{ position: 'absolute', top: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor, zIndex: 10 }} />
                    <span style={{ position: 'absolute', bottom: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor, zIndex: 10 }} />
                    <span style={{ position: 'absolute', bottom: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor, zIndex: 10 }} />
                  </>
                )}
                {card.url && <img src={card.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
    {!isMixed && lines[2]?.text&&<div style={{...defaultTextStyle,top:`${Math.min(.82,graphic.pos_y+.19)*100}%`,fontFamily:'Snell Roundhand, cursive',fontSize:width*.1,fontWeight:400,color:'#efdba2',letterSpacing:0,opacity:time-graphic.start>=Number(lines[2].offset||0)?exit:0}}>{lines[2].text}</div>}
  </div>;
}
