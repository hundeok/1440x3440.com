import Image from 'next/image';

export default function Home() {
  return (
    <main style={{ minHeight: '100vh', padding: '2rem' }}>
      
      <div className="mac-window">
        {/* Title Bar */}
        <div className="mac-titlebar">
          <div className="mac-close-btn"></div>
          <div className="mac-titlebar-text">1440x3440.com</div>
        </div>
        
        {/* Mascots */}
        <div className="mascot-left">
          {/* Pacman Ghost */}
          <svg width="80" height="80" viewBox="0 0 16 16" fill="var(--border-color)">
            <path d="M4 1h8v1h2v1h1v8h-1v2h-2v1h-2v-1h-1v1h-2v-1H6v1H4v-1H2v-1H1V3h1V2h2V1zm2 4v2h2V5H6zm4 0v2h2V5h-2z" />
          </svg>
        </div>

        <div className="mascot-right">
          {/* Space Invader */}
          <svg width="90" height="70" viewBox="0 0 11 8" fill="var(--border-color)">
            <path d="M3 0h5v1H2v1H1v1H0v2h1v1h2V5h1V4h3v1h1v1h2V3h1V1h-1V0H8v1H3V0zm-1 3v1h1V3H2zm6 0v1h1V3H8zM2 6v1h1V6H2zm6 0v1h1V6H8z"/>
          </svg>
        </div>

        <div className="mascot-left-2">
          {/* Pixel Skull / Robot */}
          <svg width="60" height="60" viewBox="0 0 16 16" fill="var(--border-color)">
            <path d="M3 3h10v2h2v4h-2v2h-2v2h-2v-2h-2v2H5v-2H3v-2H1V5h2V3zM4 6h2v2H4V6zm6 0h2v2h-2V6z" />
          </svg>
        </div>

        {/* Main Content */}
        <div className="mac-content">
          <div className="retro-alert">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2L2 21H22L12 2ZM12 6L18.8 19H5.2L12 6ZM11 11H13V15H11V11ZM11 16H13V18H11V16Z" fill="black"/>
            </svg>
            <div style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
              SYSTEM LOG: It works on my machine. ¯\_(ツ)_/¯
            </div>
          </div>

          <h1 style={{ textAlign: 'center', marginTop: '2rem' }}>1440x3440.com</h1>
          
          <p style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto 3rem auto', fontSize: '1.2rem', fontWeight: 'bold' }}>
            tired of finding stuff to put on your spare 1440x3440 or 3440x1440 portrait monitor?<br/>
            most vertical wallpapers are static. most apps are heavy and full of ads.<br/>
            just use this digital frame. it&apos;s insanely lightweight and it just works.
          </p>

          <div className="retro-image-frame">
            <div className="retro-image-inner">
              <Image 
                src="/hero-v2.jpg" 
                alt="1440x3440 App Interface" 
                width={1024} 
                height={1024}
                style={{ width: '100%', height: 'auto', display: 'block', filter: 'contrast(1.1) saturate(0.9)' }}
                priority
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center', padding: '2rem 0' }}>
            <a href="https://github.com/hundeok/1440x3440.com/releases/latest/download/PortraitFrame-mac.zip" className="retro-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M14.7 9.80005C14.7 9.80005 13.9 10.3 12.8 10.3C11.7 10.3 10.8 9.60005 9.79999 9.60005C8.39999 9.60005 7.19999 10.6 6.49999 11.8C5.09999 14.3 6.19999 18 7.59999 20C8.29999 21 9.09999 22.1 10.2 22C11.2 21.9 11.6 21.3 12.9 21.3C14.2 21.3 14.6 22 15.7 22C16.8 22 17.5 21.1 18.2 20.1C19 18.9 19.4 17.7 19.4 17.6C19.3 17.6 16.9 16.6 16.9 13.8C16.9 11.4 18.9 10.2 19 10.1C17.9 8.50005 16.1 8.30005 15.5 8.20005C14.4 8.10005 13.3 8.90005 12.6 8.90005C11.9 8.90005 11 8.20005 10.2 8.20005C9.69999 8.20005 9.19999 8.30005 8.69999 8.50005" />
                <path d="M12.9 8.10005C13.5 7.40005 13.9 6.40005 13.8 5.40005C12.9 5.40005 11.9 5.90005 11.3 6.70005C10.8 7.30005 10.3 8.30005 10.5 9.30005C11.5 9.40005 12.4 8.80005 12.9 8.10005Z" />
              </svg>
              get mac app
            </a>
            <a href="https://github.com/hundeok/1440x3440.com/releases/latest/download/PortraitFrame-win.exe" className="retro-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.5 5.5L10.5 4.5V11.5H2.5V5.5ZM11.5 4.3L21.5 3V11.5H11.5V4.3ZM2.5 12.5H10.5V19.5L2.5 18.5V12.5ZM11.5 12.5H21.5V21L11.5 19.7V12.5Z" />
              </svg>
              get win app
            </a>
            <a href="#download-appstore" className="retro-btn" style={{ background: '#000', color: '#fff', boxShadow: '3px 3px 0px 0px #aaa' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M14.7 9.80005C14.7 9.80005 13.9 10.3 12.8 10.3C11.7 10.3 10.8 9.60005 9.79999 9.60005C8.39999 9.60005 7.19999 10.6 6.49999 11.8C5.09999 14.3 6.19999 18 7.59999 20C8.29999 21 9.09999 22.1 10.2 22C11.2 21.9 11.6 21.3 12.9 21.3C14.2 21.3 14.6 22 15.7 22C16.8 22 17.5 21.1 18.2 20.1C19 18.9 19.4 17.7 19.4 17.6C19.3 17.6 16.9 16.6 16.9 13.8C16.9 11.4 18.9 10.2 19 10.1C17.9 8.50005 16.1 8.30005 15.5 8.20005C14.4 8.10005 13.3 8.90005 12.6 8.90005C11.9 8.90005 11 8.20005 10.2 8.20005C9.69999 8.20005 9.19999 8.30005 8.69999 8.50005" />
                <path d="M12.9 8.10005C13.5 7.40005 13.9 6.40005 13.8 5.40005C12.9 5.40005 11.9 5.90005 11.3 6.70005C10.8 7.30005 10.3 8.30005 10.5 9.30005C11.5 9.40005 12.4 8.80005 12.9 8.10005Z" />
              </svg>
              Mac App Store

            </a>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '2rem', borderTop: '2px solid #000', paddingTop: '2rem', marginTop: '2rem' }}>
            <div style={{ border: '2px solid #000', padding: '1rem', background: '#fff' }}>
              <strong style={{ fontSize: '1.2rem', display: 'block', borderBottom: '2px solid #000', paddingBottom: '0.5rem', marginBottom: '1rem' }}>Zero_Ads</strong>
              <span style={{ fontSize: '0.9rem' }}>no ads. no subscriptions. just pure 60fps streaming.</span>
            </div>
            <div style={{ border: '2px solid #000', padding: '1rem', background: '#fff' }}>
              <strong style={{ fontSize: '1.2rem', display: 'block', borderBottom: '2px solid #000', paddingBottom: '0.5rem', marginBottom: '1rem' }}>Zero_Storage</strong>
              <span style={{ fontSize: '0.9rem' }}>doesn&apos;t eat your SSD. streams directly to memory.</span>
            </div>
          </div>

        </div>
      </div>
      
      {/* README Window */}
      <div className="mac-window" style={{ maxWidth: '800px', marginTop: '-1rem', position: 'relative', zIndex: 10 }}>
        <div className="mac-titlebar">
          <div className="mac-close-btn"></div>
          <div className="mac-titlebar-text">README.txt</div>
        </div>
        <div className="mac-content" style={{ background: '#fff', padding: '2rem', textAlign: 'left' }}>
          <p style={{ margin: '0 0 1.5rem 0', fontWeight: 'bold', fontSize: '1.2rem', textTransform: 'uppercase' }}>How to use this thing:</p>
          
          <ul style={{ listStyleType: 'none', padding: 0, margin: 0, lineHeight: '2.5', fontSize: '1.1rem' }}>
            <li>
              <strong style={{ background: '#000', color: '#fff', padding: '4px 8px', border: '2px solid #000', marginRight: '10px' }}>[TAB]</strong> 
              Toggle Options Menu (because visible buttons are ugly)
            </li>
            <li>
              <strong style={{ background: '#000', color: '#fff', padding: '4px 8px', border: '2px solid #000', marginRight: '10px' }}>[SPACE]</strong> 
              Force Next Image (if you&apos;re impatient)
            </li>
            <li>
              <strong style={{ background: '#000', color: '#fff', padding: '4px 8px', border: '2px solid #000', marginRight: '10px' }}>[ESC]</strong> 
              Close App
            </li>
          </ul>
          
          <div style={{ margin: '2rem 0 0 0', borderTop: '2px dashed #000', paddingTop: '1.5rem', fontSize: '1rem', lineHeight: '1.6' }}>
            <strong>MECHANISM:</strong><br/>
            This app fetches a manifest (`images.json`) directly from a public Cloudflare R2 bucket. It caches images strictly to RAM up to a specified limit. Slide intervals and playlist sync happen automatically in the background. <br/><br/>
            * Don&apos;t email me for customer support. I made this for myself.
          </div>
        </div>
      </div>
      
      <div style={{ textAlign: 'center', marginTop: '4rem', fontWeight: 'bold', marginBottom: '2rem' }}>
        <p style={{ marginBottom: '1rem' }}>built by a guy with a spare 3440x1440 monitor.</p>
        <a href="https://ko-fi.com/hdcho" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '0.5rem 1rem', background: '#000', color: '#fff', textDecoration: 'none', border: '2px solid #000', boxShadow: '2px 2px 0px #aaa' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="#FF5E5B" xmlns="http://www.w3.org/2000/svg">
            <path d="M23.881 8.948c-.773-4.085-4.859-4.593-4.859-4.593H.723c-.604 0-.679.798-.679.798s-.082 7.324-.022 11.822c.164 2.424 2.586 2.672 2.586 2.672s8.267-.023 11.966-.049c2.438-.426 2.683-2.566 2.658-3.734 4.352.24 7.422-2.831 6.649-6.916zm-11.062 3.511c-1.246 1.453-4.011 3.976-4.011 3.976s-.121.119-.31.023c-.076-.057-.108-.09-.108-.09-.443-.441-3.368-3.049-4.034-3.954-.709-.965-1.041-2.7-.091-3.71.951-1.01 3.005-1.086 4.363.407 0 0 1.565-1.782 3.468-.963 1.904.82 1.832 3.011.723 4.311zm6.173.478c-.928.116-1.682.028-1.682.028V7.284h1.77s1.971.551 1.971 2.638c0 1.913-.985 2.667-2.059 3.015z"/>
          </svg>
          Buy me a coffee
        </a>
      </div>
    </main>
  );
}
