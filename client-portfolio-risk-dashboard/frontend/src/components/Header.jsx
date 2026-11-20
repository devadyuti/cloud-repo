import React from 'react';
import TopNavigation from '@cloudscape-design/components/top-navigation';

/**
 * Header component using Cloudscape TopNavigation.
 * Displays the Wealth Management branding with Navy Blue background.
 */
function Header() {
  return (
    <div className="header-wrapper">
      <TopNavigation
        identity={{
          href: '#',
          title: '🏦 Wealth Management',
          logo: undefined,
        }}
        utilities={[]}
        i18nStrings={{
          overflowMenuTriggerText: 'More',
          overflowMenuTitleText: 'All',
        }}
      />
    </div>
  );
}

export default Header;
