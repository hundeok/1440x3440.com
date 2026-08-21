import Image from 'next/image';

export default function Home() {
  return (
    <main style={{ minHeight: '100vh', padding: '2rem' }}>
      
      <div className="mac-window">
        {/* Title Bar */}
        <div className="mac-titlebar">
          <div className="mac-close-btn"></div>
          <div className="mac-titlebar-text">3440x1440.com</div>
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

          <h1 style={{ textAlign: 'center', marginTop: '2rem' }}>3440x1440.com</h1>
          
          <p style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto 3rem auto', fontSize: '1.2rem', fontWeight: 'bold' }}>
            tired of finding stuff to put on your spare 3440x1440 monitor?<br/>
            some apps are too heavy. some are full of ads.<br/>
            just use this. it's insanely lightweight and it just works.
          </p>

          <div className="retro-image-frame">
            <div className="retro-image-inner">
              <Image 
                src="/hero-v2.jpg" 
                alt="3440x1440 App Interface" 
                width={1024} 
                height={1024}
                style={{ width: '100%', height: 'auto', display: 'block', filter: 'contrast(1.1) saturate(0.9)' }}
                priority
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center', padding: '2rem 0' }}>
            <a href="#download-mac" className="retro-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M14.7 9.80005C14.7 9.80005 13.9 10.3 12.8 10.3C11.7 10.3 10.8 9.60005 9.79999 9.60005C8.39999 9.60005 7.19999 10.6 6.49999 11.8C5.09999 14.3 6.19999 18 7.59999 20C8.29999 21 9.09999 22.1 10.2 22C11.2 21.9 11.6 21.3 12.9 21.3C14.2 21.3 14.6 22 15.7 22C16.8 22 17.5 21.1 18.2 20.1C19 18.9 19.4 17.7 19.4 17.6C19.3 17.6 16.9 16.6 16.9 13.8C16.9 11.4 18.9 10.2 19 10.1C17.9 8.50005 16.1 8.30005 15.5 8.20005C14.4 8.10005 13.3 8.90005 12.6 8.90005C11.9 8.90005 11 8.20005 10.2 8.20005C9.69999 8.20005 9.19999 8.30005 8.69999 8.50005" />
                <path d="M12.9 8.10005C13.5 7.40005 13.9 6.40005 13.8 5.40005C12.9 5.40005 11.9 5.90005 11.3 6.70005C10.8 7.30005 10.3 8.30005 10.5 9.30005C11.5 9.40005 12.4 8.80005 12.9 8.10005Z" />
              </svg>
              get mac app
            </a>
            <a href="#download-win" className="retro-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.5 5.5L10.5 4.5V11.5H2.5V5.5ZM11.5 4.3L21.5 3V11.5H11.5V4.3ZM2.5 12.5H10.5V19.5L2.5 18.5V12.5ZM11.5 12.5H21.5V21L11.5 19.7V12.5Z" />
              </svg>
              get win app
            </a>
            <a href="#download-appstore" className="retro-btn" style={{ background: '#000', color: '#fff', boxShadow: '3px 3px 0px 0px #aaa' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4H8C5.79 4 4 5.79 4 8V16C4 18.21 5.79 20 8 20H16C18.21 20 20 18.21 20 16V8C20 5.79 18.21 4 16 4ZM15 13H9V11H15V13Z" />
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
              <span style={{ fontSize: '0.9rem' }}>doesn't eat your SSD. streams directly to memory.</span>
            </div>
          </div>

        </div>
      </div>
      
      <div style={{ textAlign: 'center', marginTop: '4rem', fontWeight: 'bold', marginBottom: '2rem' }}>
        built by a guy with a spare 3440x1440 monitor.
      </div>
    </main>
  );
}
